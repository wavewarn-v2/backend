# src/wavewarn/routes/risk.py

"""
WaveWarn Model-backed Risk Routes

Paths:
- /risk/model/live
- /risk/model/timeline
- /risk/model/forecast
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
import httpx
from datetime import datetime, timezone, timedelta
from ..models import RiskPoint, RiskTimeline

from ..utils.openmeteo_air_client import fetch_air_quality
from ..utils.forecast_utils import group_hourly_to_daily, daily_mean, daily_max, decay_extrapolate
from ..utils.openmeteo_weather_client import fetch_weather_hourly
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/risk/model", tags=["risk-model"])


def score_hourly(temp_c: float | None, rh: float | None) -> int:
    if temp_c is None or rh is None:
        return 0

    s = (float(temp_c) * 2.0) + (float(rh) * 0.3) - 20
    s = 0 if s < 0 else (100 if s > 100 else s)
    return int(round(s))


def tier_from_score(score: int) -> str:
    if score >= 80:
        return "extreme"
    if score >= 60:
        return "high"
    if score >= 40:
        return "moderate"
    if score >= 20:
        return "caution"
    return "safe"


def drivers_from_score(score: int) -> Dict[str, float]:
    return {
        "heat_index": round(score * 0.60, 2),
        "humidity_load": round(score * 0.30, 2),
        "clear_sky_risk": round(score * 0.10, 2),
    }


def hourly_insight(tier: str, temp, rh, wind, radiation) -> str:
    if tier in ["extreme", "high"]:
        if rh is not None and rh >= 65:
            return "Hot and humid • Take cooling breaks."
        if wind is not None and wind <= 5:
            return "High heat, weak wind • Limit exposure."
        if radiation is not None and radiation >= 500:
            return "Strong sun exposure • Seek shade."
        return "High heat risk • Avoid peak exposure."

    if tier == "moderate":
        return "Moderate heat stress • Stay hydrated."

    if tier == "caution":
        return "Mild heat caution • Use shade."

    return "Safe conditions • Normal activity okay."


def daily_insight(heat_tier: str, aq_tier_value: str | None, peak_hour) -> str:
    heat_text = {
        "safe": "Safe heat",
        "caution": "Mild heat",
        "moderate": "Moderate heat",
        "high": "High heat",
        "extreme": "Extreme heat",
    }.get(heat_tier, "Heat risk")

    aq_text = {
        "good": "good AQI",
        "moderate": "moderate AQI",
        "unhealthy_sensitive": "sensitive AQI",
        "unhealthy": "poor AQI",
        "very_unhealthy": "very poor AQI",
        "hazardous": "hazardous AQI",
    }.get(aq_tier_value, None)

    if peak_hour is None:
        if aq_text:
            return f"{heat_text}, {aq_text}"
        return heat_text

    if aq_text:
        return f"{heat_text}, {aq_text} • Peak around {peak_hour}:00"

    return f"{heat_text} • Peak around {peak_hour}:00"


def get_daily_air_quality(lat: float, lon: float, days: int) -> Dict[str, Dict[str, Any]]:
    try:
        aq_days = min(days, 5)
        extend_days = max(0, min(5, days - aq_days))

        aq = fetch_air_quality(lat, lon, days=aq_days)
        hh = aq.get("hourly", {})

        times = hh.get("time", [])
        pm25 = hh.get("pm2_5", []) or []
        ozone_ugm3 = hh.get("ozone", []) or []
        ozone_ppb = [None if v is None else float(v) / 2.0 for v in ozone_ugm3]

        pm25_by_day = group_hourly_to_daily(times, pm25)
        o3_by_day = group_hourly_to_daily(times, ozone_ppb)

        pm25_daily = daily_mean(pm25_by_day)
        o3_daily = daily_mean(o3_by_day)

        days_sorted = sorted(pm25_daily.keys() | o3_daily.keys())
        out: Dict[str, Dict[str, Any]] = {}

        for d in days_sorted:
            p = pm25_daily.get(d)
            o = o3_daily.get(d)

            a_pm25 = aqi_pm25(p)
            a_o3 = aqi_o3(o)
            a_all = aqi_overall(p, o)

            out[d] = {
                "aqi": a_all,
                "tier": aqi_tier(a_all),
                "pm25_ugm3": p,
                "o3_ppb": o,
                "source": "Open-Meteo AQ",
                "confidence": "high",
                "components": {"pm25": a_pm25, "o3": a_o3},
            }

        if extend_days == 0 or not days_sorted:
            return out

        wx = fetch_weather_hourly(lat, lon, days=min(10, days))
        wh = wx.get("hourly", {})

        wt = wh.get("time", [])
        t2m = wh.get("temperature_2m", []) or []
        wspd = wh.get("wind_speed_10m", []) or []

        t_by_day = group_hourly_to_daily(wt, t2m)
        w_by_day = group_hourly_to_daily(wt, wspd)

        t_daily_max = daily_max(t_by_day)
        w_daily_mean = daily_mean(w_by_day)

        last_aq_date = days_sorted[-1]
        ref_t = t_daily_max.get(last_aq_date) or 30.0
        ref_w = w_daily_mean.get(last_aq_date) or 2.0

        last_pm25 = pm25_daily.get(last_aq_date)
        last_o3 = o3_daily.get(last_aq_date)

        pm25_decay = decay_extrapolate(last_pm25, extend_days, half_life_days=3.0)
        o3_decay = decay_extrapolate(last_o3, extend_days, half_life_days=3.0)

        wx_days_sorted = sorted(t_daily_max.keys())

        for i in range(extend_days):
            try:
                idx = wx_days_sorted.index(last_aq_date) + (i + 1)
            except Exception:
                idx = len(days_sorted) + i

            if idx >= len(wx_days_sorted):
                continue

            d = wx_days_sorted[idx]
            tmax = t_daily_max.get(d, ref_t)
            wavg = w_daily_mean.get(d, ref_w)

            temp_adj = min(0.20, max(-0.20, 0.03 * ((tmax - ref_t) / 2.0)))
            wind_adj_pm = min(0.20, max(-0.20, -0.03 * ((wavg - ref_w) / 2.0)))
            wind_adj_o3 = min(0.20, max(-0.20, 0.01 * ((wavg - ref_w) / 2.0)))

            base_pm = pm25_decay[i] if pm25_decay else None
            base_o3 = o3_decay[i] if o3_decay else None

            pm_est = None if base_pm is None else max(0.0, base_pm * (1.0 + temp_adj + wind_adj_pm))
            o3_est = None if base_o3 is None else max(0.0, base_o3 * (1.0 + temp_adj + wind_adj_o3))

            a_pm25 = aqi_pm25(pm_est)
            a_o3 = aqi_o3(o3_est)
            a_all = aqi_overall(pm_est, o3_est)

            out[d] = {
                "aqi": a_all,
                "tier": aqi_tier(a_all),
                "pm25_ugm3": pm_est,
                "o3_ppb": o3_est,
                "source": "Extrapolated (AQ decay + met adj)",
                "confidence": "low",
                "components": {"pm25": a_pm25, "o3": a_o3},
            }

        return out

    except Exception:
        return {}


def build_openmeteo_hourly_url(lat: float, lon: float, hours: int) -> str:
    days = max(1, min(16, (hours + 23) // 24))

    return (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,"
        f"shortwave_radiation,cloud_cover"
        f"&forecast_days={days}"
        f"&timezone=auto"
    )


def fetch_openmeteo_hourly(lat: float, lon: float, hours: int) -> dict:
    url = build_openmeteo_hourly_url(lat, lon, hours)

    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers={"Accept": "application/json"})

    r.raise_for_status()
    return r.json()


@router.get("/live", response_model=dict)
def model_live_risk(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    try:
        js = fetch_openmeteo_hourly(lat, lon, hours=1)
        h = js.get("hourly", {})

        temps = h.get("temperature_2m", [])
        rhs = h.get("relative_humidity_2m", [])
        winds = h.get("wind_speed_10m", [])
        radiation = h.get("shortwave_radiation", [])
        clouds = h.get("cloud_cover", [])

        t_now = temps[0] if temps else None
        rh_now = rhs[0] if rhs else None
        wind_now = winds[0] if winds else 0
        radiation_now = radiation[0] if radiation else 0
        cloud_now = clouds[0] if clouds else 0

        score = score_hourly(t_now, rh_now)
        tier = tier_from_score(score)
        drivers = drivers_from_score(score)

        return {
            "ok": True,
            "when": datetime.now(timezone.utc).isoformat(),
            "location": {
                "lat": lat,
                "lon": lon,
            },
            "score": score,
            "tier": tier,
            "weather": {
                "temperature_c": t_now,
                "humidity_percent": rh_now,
                "wind_speed_kmh": wind_now,
                "solar_radiation": radiation_now,
                "cloud_cover_percent": cloud_now,
            },
            "drivers": drivers,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Open-Meteo fetch/compute failed: {e}",
        )


@router.get("/timeline", response_model=RiskTimeline)
def model_risk_timeline(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    hours: int = Query(24, ge=1, le=72, description="How many hours ahead"),
):
    try:
        js = fetch_openmeteo_hourly(lat, lon, hours=hours)
        h = js.get("hourly", {})

        temps = h.get("temperature_2m", [])
        rhs = h.get("relative_humidity_2m", [])

        points: List[RiskPoint] = []

        now = datetime.now(timezone.utc).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        total_points = min(
            hours,
            len(temps),
            len(rhs) if rhs else hours,
        )

        for i in range(total_points):
            hour_local = (now + timedelta(hours=i)).hour

            temp_value = temps[i] if i < len(temps) else None
            rh_value = rhs[i] if i < len(rhs) else None

            s = score_hourly(temp_value, rh_value)

            points.append(
                RiskPoint(
                    hour=hour_local,
                    score=int(s),
                    tier=tier_from_score(s),
                    drivers=drivers_from_score(s),
                )
            )

        return RiskTimeline(
            ok=True,
            location={
                "lat": lat,
                "lon": lon,
            },
            points=points,
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Open-Meteo fetch/compute failed: {e}",
        )


@router.get("/forecast", response_model=dict)
def model_10_day_forecast(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(10, ge=1, le=10, description="Forecast days"),
):
    try:
        hours = days * 24
        js = fetch_openmeteo_hourly(lat, lon, hours=hours)
        daily_aq = get_daily_air_quality(lat, lon, days)

        h = js.get("hourly", {})

        times = h.get("time", [])
        temps = h.get("temperature_2m", [])
        rhs = h.get("relative_humidity_2m", [])
        winds = h.get("wind_speed_10m", [])
        radiation = h.get("shortwave_radiation", [])
        clouds = h.get("cloud_cover", [])

        days_map = {}

        total = min(
            hours,
            len(times),
            len(temps),
            len(rhs),
        )

        for i in range(total):
            time_value = times[i]

            date_part = time_value.split("T")[0]
            hour_part = int(time_value.split("T")[1].split(":")[0])

            temp = temps[i] if i < len(temps) else None
            rh = rhs[i] if i < len(rhs) else None
            wind = winds[i] if i < len(winds) else 0
            rad = radiation[i] if i < len(radiation) else 0
            cloud = clouds[i] if i < len(clouds) else 0

            risk_score = score_hourly(temp, rh)
            risk_tier = tier_from_score(risk_score)

            hour_obj = {
                "hour": hour_part,
                "weather": {
                    "temperature_c": temp,
                    "humidity_percent": rh,
                    "wind_speed_kmh": wind,
                    "solar_radiation": rad,
                    "cloud_cover_percent": cloud,
                },
                "risk": {
                    "score": risk_score,
                    "tier": risk_tier,
                    "drivers": drivers_from_score(risk_score),
                    "insight": hourly_insight(risk_tier, temp, rh, wind, rad),
                },
            }

            if date_part not in days_map:
                days_map[date_part] = {
                    "date": date_part,
                    "hourly": [],
                }

            days_map[date_part]["hourly"].append(hour_obj)

        final_days = []

        for _, day_data in days_map.items():
            hourly = day_data["hourly"]

            scores = [x["risk"]["score"] for x in hourly]

            max_score = max(scores) if scores else 0
            min_score = min(scores) if scores else 0
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0

            peak_hour = (
                max(hourly, key=lambda x: x["risk"]["score"])["hour"]
                if hourly
                else None
            )

            safest_hour = (
                min(hourly, key=lambda x: x["risk"]["score"])["hour"]
                if hourly
                else None
            )

            temps_day = [
                x["weather"]["temperature_c"]
                for x in hourly
                if x["weather"]["temperature_c"] is not None
            ]

            humidity_day = [
                x["weather"]["humidity_percent"]
                for x in hourly
                if x["weather"]["humidity_percent"] is not None
            ]

            daily_tier = tier_from_score(int(avg_score))
            aq_for_day = daily_aq.get(day_data["date"])
            aq_tier_value = aq_for_day.get("tier") if aq_for_day else None

            day_data["daily"] = {
                "max_score": max_score,
                "min_score": min_score,
                "avg_score": avg_score,
                "tier": daily_tier,
                "peak_hour": peak_hour,
                "safest_hour": safest_hour,
                "max_temperature_c": max(temps_day) if temps_day else None,
                "min_temperature_c": min(temps_day) if temps_day else None,
                "avg_humidity_percent": (
                    round(sum(humidity_day) / len(humidity_day), 2)
                    if humidity_day
                    else None
                ),
                "air_quality": aq_for_day,
                "insight": daily_insight(daily_tier, aq_tier_value, peak_hour),
            }

            final_days.append(day_data)

        return {
            "ok": True,
            "location": {
                "lat": lat,
                "lon": lon,
            },
            "days_requested": days,
            "days_returned": len(final_days),
            "days": final_days,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"10-day forecast failed: {e}",
        )
