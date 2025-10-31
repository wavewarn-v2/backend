# src/wavewarn/routes/forecast_air_summary.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from ..utils.openmeteo_air_client import fetch_air_quality, OMAirError
from ..utils.openmeteo_weather_client import fetch_weather_hourly, OMWeatherError
from ..utils.forecast_utils import group_hourly_to_daily, daily_mean, daily_max, decay_extrapolate
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/forecast/air", tags=["forecast"])

@router.get("/summary")
def air_forecast_summary(
    lat: float = Query(...),
    lon: float = Query(...),
    aq_days: int = Query(5, ge=1, le=5, description="Air-quality forecast days (max 5)"),
    extend_days: int = Query(5, ge=0, le=5, description="How many extra days to extrapolate (0–5)")
) -> Dict[str, Any]:
    """
    Returns daily AQ summary:
      Days 1–aq_days: from Open-Meteo Air Quality hourly forecast (rolled to daily mean).
      Days aq_days+1–aq_days+extend_days: extrapolated from last AQ day using a decay,
      lightly adjusted by meteorology (temp max & wind).
    """
    try:
        # --- 1) AQ forecast (hourly) up to 5 days ---
        aq = fetch_air_quality(lat, lon, days=aq_days)
        hh = aq.get("hourly", {})
        times = hh.get("time", [])
        pm25 = hh.get("pm2_5", []) or []
        ozone_ugm3 = hh.get("ozone", []) or []
        # Convert ozone µg/m³ -> ~ppb
        ozone_ppb = [None if v is None else float(v) / 2.0 for v in ozone_ugm3]

        pm25_by_day = group_hourly_to_daily(times, pm25)
        o3_by_day = group_hourly_to_daily(times, ozone_ppb)

        pm25_daily = daily_mean(pm25_by_day)
        o3_daily   = daily_mean(o3_by_day)

        # Build day list in order present in AQ (sorted by date)
        days_sorted = sorted(pm25_daily.keys() | o3_daily.keys())

        daily_rows: List[Dict[str, Any]] = []
        for d in days_sorted:
            p = pm25_daily.get(d)
            o = o3_daily.get(d)
            a_pm25 = aqi_pm25(p)
            a_o3 = aqi_o3(o)
            a_all = aqi_overall(p, o)
            daily_rows.append({
                "date": d,
                "source": "Open-Meteo AQ",
                "confidence": "high",
                "pm25_ugm3": p,
                "o3_ppb": o,
                "aqi": {"pm25": a_pm25, "o3": a_o3, "overall": a_all, "tier": aqi_tier(a_all)}
            })

        # If no extension requested, return here
        if extend_days == 0:
            return {
                "ok": True,
                "location": {"lat": lat, "lon": lon},
                "days": daily_rows
            }

        # --- 2) Weather (hourly) for 10 days to adjust extrapolation ---
        wx = fetch_weather_hourly(lat, lon, days=min(10, aq_days + extend_days))
        wh = wx.get("hourly", {})
        wt = wh.get("time", [])
        t2m  = wh.get("temperature_2m", []) or []
        wspd = wh.get("wind_speed_10m", []) or []

        t_by_day = group_hourly_to_daily(wt, t2m)
        w_by_day = group_hourly_to_daily(wt, wspd)

        t_daily_max = daily_max(t_by_day)  # use daily max temp
        w_daily_mean = daily_mean(w_by_day)

        # Reference for met adjustment = last AQ day’s temp max & wind mean
        last_aq_date = days_sorted[-1] if days_sorted else None
        ref_t = (t_daily_max.get(last_aq_date) if last_aq_date else None) or 30.0
        ref_w = (w_daily_mean.get(last_aq_date) if last_aq_date else None) or 2.0

        # Base for extrapolation = last available AQ day means
        last_pm25 = pm25_daily.get(last_aq_date) if last_aq_date else None
        last_o3   = o3_daily.get(last_aq_date) if last_aq_date else None

        # Exponential decay baseline across extend_days
        pm25_decay = decay_extrapolate(last_pm25, extend_days, half_life_days=3.0)
        o3_decay   = decay_extrapolate(last_o3,   extend_days, half_life_days=3.0)

        # Build extrapolated days
        # Simple met adjustment:
        #   warmer than ref_t → +3% per 2°C for PM2.5 and O3 (capped ±20%)
        #   windier than ref_w → -3% per 2 m/s for PM2.5 (+ventilation), +1% per 2 m/s for O3 mixing (caps)
        ext_rows: List[Dict[str, Any]] = []
        for i in range(extend_days):
            # pick the i-th calendar day after last_aq_date present in weather
            # choose by sorting weather day keys and picking next ones
            wx_days_sorted = sorted(t_daily_max.keys())
            # find index of last_aq_date
            try:
                idx = wx_days_sorted.index(last_aq_date) + (i + 1)
            except Exception:
                idx = i  # fallback
            d = wx_days_sorted[idx] if idx < len(wx_days_sorted) else f"+{i+1}d"

            tmax = t_daily_max.get(d, ref_t)
            wavg = w_daily_mean.get(d, ref_w)

            # adjustments
            temp_adj = min(0.20, max(-0.20, 0.03 * ((tmax - ref_t) / 2.0)))   # ±20% cap
            wind_adj_pm = min(0.20, max(-0.20, -0.03 * ((wavg - ref_w) / 2.0)))
            wind_adj_o3 = min(0.20, max(-0.20,  0.01 * ((wavg - ref_w) / 2.0)))

            base_pm = pm25_decay[i] if pm25_decay else None
            base_o3 = o3_decay[i]   if o3_decay   else None

            pm_est = None if base_pm is None else max(0.0, base_pm * (1.0 + temp_adj + wind_adj_pm))
            o3_est = None if base_o3 is None else max(0.0, base_o3 * (1.0 + temp_adj + wind_adj_o3))

            a_pm25 = aqi_pm25(pm_est)
            a_o3   = aqi_o3(o3_est)
            a_all  = aqi_overall(pm_est, o3_est)

            ext_rows.append({
                "date": d,
                "source": "Extrapolated (AQ decay + met adj)",
                "confidence": "low",
                "pm25_ugm3": pm_est,
                "o3_ppb": o3_est,
                "aqi": {"pm25": a_pm25, "o3": a_o3, "overall": a_all, "tier": aqi_tier(a_all)}
            })

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "days": daily_rows + ext_rows
        }

    except (OMAirError, OMWeatherError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Air summary build failed: {e}")

