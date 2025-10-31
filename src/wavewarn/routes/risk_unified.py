# src/wavewarn/routes/risk_unified.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional

from ..utils.settings import CFG
from ..utils.weather_provider import get_hourly_weather, WeatherProviderError
from ..utils.openmeteo_air_client import fetch_air_quality, OMAirError
from ..utils.heat_math import heat_index_c, wbgt_shade_c, tier_from_heat
from ..utils.aqi import aqi_overall, aqi_tier
from ..utils.risk_unified import combine_tiers

router = APIRouter(prefix="/risk", tags=["risk"])

@router.get("/unified/hourly")
def unified_hourly(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(5, ge=1, le=5, description="Hourly horizon; matches AQ’s 1–5 day limit"),
    w_heat: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_aqi:  Optional[float] = Query(None, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    Hourly unified risk by fusing Heat (weather provider) + AQI (Open-Meteo air).
    If weights not provided, defaults come from runtime config.
    """
    try:
        weight_heat = w_heat if w_heat is not None else CFG.weight_heat
        weight_aqi  = w_aqi  if w_aqi  is not None else CFG.weight_aqi

        wx = get_hourly_weather(lat, lon, days=days)
        aq = fetch_air_quality(lat, lon, days=days)

        wt = wx.get("hourly", {}) or {}
        at = aq.get("hourly", {}) or {}

        times_wx: List[str] = wt.get("time", []) or []
        times_aq: List[str] = at.get("time", []) or []
        n = min(len(times_wx), len(times_aq))
        if n == 0:
            return {"ok": False, "msg": "No overlapping hourly timestamps between weather and air."}

        t2m  = (wt.get("temperature_2m", []) or [])[:n]
        rh2m = (wt.get("relative_humidity_2m", []) or [])[:n]
        pm25 = (at.get("pm2_5", []) or [])[:n]
        o3ug = (at.get("ozone",  []) or [])[:n]
        o3ppb = [None if v is None else float(v)/2.0 for v in o3ug]

        out: List[Dict[str, Any]] = []
        for i in range(n):
            ts = times_wx[i]
            t, rh = t2m[i], rh2m[i]
            p, o  = pm25[i], o3ppb[i]

            hi = heat_index_c(t, rh)
            wb = wbgt_shade_c(t, rh)
            heat_tier = tier_from_heat(hi, wb)

            a_all = aqi_overall(p, o)
            aqi_t = aqi_tier(a_all)

            score, tier = combine_tiers(heat_tier, aqi_t, w_heat=weight_heat, w_aqi=weight_aqi)

            out.append({
                "ts": ts,
                "t_c": t, "rh_pct": rh,
                "pm25_ugm3": p, "o3_ppb": o,
                "heat": {"heat_index_c": hi, "wbgt_shade_c": wb, "tier": heat_tier},
                "aqi":  {"overall": a_all, "tier": aqi_t},
                "combined": {"score": score, "tier": tier}
            })

        order = {"unknown":0, "safe":1, "caution":2, "risk":3, "extreme":4}
        peak = max(out, key=lambda r: (order.get(r["combined"]["tier"], 0), r["combined"]["score"])) if out else None

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "hours": len(out),
            "weights": {"heat": weight_heat, "aqi": weight_aqi},
            "provider_weather": wx.get("provider"),
            "peak": peak,
            "timeline": out,
            "source": "Weather provider (OM/OWM) + Open-Meteo Air → WaveWarn fusion"
        }

    except (WeatherProviderError, OMAirError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unified risk build failed: {e}")

