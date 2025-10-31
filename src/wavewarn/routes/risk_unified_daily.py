# src/wavewarn/routes/risk_unified_daily.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional

from ..utils.settings import CFG
from ..utils.weather_provider import get_hourly_weather, WeatherProviderError
from ..utils.openmeteo_air_client import fetch_air_quality, OMAirError
from ..utils.heat_math import heat_index_c, wbgt_shade_c, tier_from_heat
from ..utils.aqi import aqi_overall, aqi_tier
from ..utils.risk_unified import combine_tiers
from ..utils.daily_reduce import group_by_day, reduce_day
from ..routes.forecast_air_summary import air_forecast_summary
from ..utils.waqi_client import fetch_geo, extract_latest, WAQIError
from ..utils.aq_blend import blend_day1_with_waqi

router = APIRouter(prefix="/risk", tags=["risk"])

@router.get("/unified/daily")
def unified_daily(
    lat: float = Query(...),
    lon: float = Query(...),
    days_hourly: int = Query(5, ge=1, le=5, description="Days with hourly AQ (1–5)"),
    extend_days: int = Query(5, ge=0, le=5, description="Extra days using AQ extrapolation (0–5)"),
    w_heat: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_aqi:  Optional[float] = Query(None, ge=0.0, le=1.0),
    use_waqi_day1: bool = Query(True, description="Override Day 1 with live WAQI when available")
) -> Dict[str, Any]:
    try:
        weight_heat = w_heat if w_heat is not None else CFG.weight_heat
        weight_aqi  = w_aqi  if w_aqi  is not None else CFG.weight_aqi

        wx = get_hourly_weather(lat, lon, days=days_hourly)
        aq = fetch_air_quality(lat, lon, days=days_hourly)

        wt = wx.get("hourly", {}) or {}
        at = aq.get("hourly", {}) or {}

        times: List[str] = wt.get("time", []) or []
        t2m:   List[Optional[float]] = wt.get("temperature_2m", []) or []
        rh2m:  List[Optional[float]] = wt.get("relative_humidity_2m", []) or []
        pm25:  List[Optional[float]] = at.get("pm2_5", []) or []
        o3ug:  List[Optional[float]] = at.get("ozone", []) or []
        o3ppb = [None if v is None else float(v)/2.0 for v in o3ug]

        n = min(len(times), len(t2m), len(rh2m), len(pm25), len(o3ppb))
        if n == 0:
            return {"ok": False, "msg": "No overlapping hourly data to aggregate."}

        hourly_rows: List[Dict[str, Any]] = []
        for i in range(n):
            ts = times[i]
            t, rh = t2m[i], rh2m[i]
            p, o  = pm25[i], o3ppb[i]

            hi = heat_index_c(t, rh)
            wb = wbgt_shade_c(t, rh)
            heat_t = tier_from_heat(hi, wb)

            a_all = aqi_overall(p, o)
            a_t   = aqi_tier(a_all)

            score, tier = combine_tiers(heat_t, a_t, w_heat=weight_heat, w_aqi=weight_aqi)
            hourly_rows.append({"ts": ts, "combined": {"score": score, "tier": tier}})

        by_day = group_by_day(hourly_rows)
        days_partA: List[Dict[str, Any]] = []
        for day in sorted(by_day.keys()):
            red = reduce_day(by_day[day])
            days_partA.append({
                "date": day,
                "score": red["score_max"],
                "tier": red["tier_max"],
                "confidence": "high"
            })

        if use_waqi_day1 and days_partA:
            try:
                data = fetch_geo(lat, lon)
                latest = extract_latest(data)
                waqi_payload = {"pm25_ugm3": latest.get("pm25"), "o3_ppb": latest.get("o")}
                days_partA[0] = blend_day1_with_waqi(days_partA[0], waqi_payload)
            except WAQIError:
                pass

        days_partB: List[Dict[str, Any]] = []
        if extend_days > 0:
            ext = air_forecast_summary(lat, lon, aq_days=days_hourly, extend_days=extend_days)
            if isinstance(ext, dict) and ext.get("ok"):
                for r in ext.get("days", []):
                    if r.get("confidence") == "low":
                        days_partB.append({
                            "date": r["date"],
                            "score": r["aqi"]["overall"],
                            "tier":  r["aqi"]["tier"],
                            "confidence": "low"
                        })

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "weights": {"heat": weight_heat, "aqi": weight_aqi},
            "provider_weather": wx.get("provider"),
            "days": days_partA + days_partB
        }

    except (WeatherProviderError, OMAirError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unified daily build failed: {e}")

