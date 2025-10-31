# src/wavewarn/routes/risk_heat.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from ..utils.weather_provider import get_weather_hourly, WeatherProviderError
from ..utils.heat_math import heat_index_c, wbgt_shade_c, tier_from_heat

router = APIRouter(prefix="/risk", tags=["risk"])

def _iso_date(ts: str) -> str:
    return ts.split("T")[0] if "T" in ts else ts[:10]

@router.get("/heat/hourly")
def heat_hourly(
    lat: float = Query(...),
    lon: float = Query(...),
    provider: str = Query("openmeteo", description="openmeteo | openweather | auto"),
    days: int = Query(5, ge=1, le=10),
) -> Dict[str, Any]:
    try:
        wx = get_weather_hourly(lat, lon, provider=provider, days=days)
        hourly = wx.get("hourly", {})
        times: List[str] = hourly.get("time", []) or []
        t2m:   List[Optional[float]] = hourly.get("temperature_2m", []) or []
        rh2m:  List[Optional[float]] = hourly.get("relative_humidity_2m", []) or []
        out = []
        n = min(len(times), len(t2m), len(rh2m))
        for i in range(n):
            t, rh = t2m[i], rh2m[i]
            if t is None or rh is None:
                continue
            hi = heat_index_c(t, rh)
            wb = wbgt_shade_c(t, rh)
            out.append({"ts": times[i], "t_c": t, "rh_pct": rh, "hi_c": hi, "wbgt_c": wb,
                        "tier": tier_from_heat(hi, wb)})
        return {"ok": True, "provider": wx.get("provider"), "hours": len(out), "timeline": out}
    except WeatherProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Heat hourly failed: {e}")


@router.get("/heat/daily")
def heat_daily(
    lat: float = Query(...),
    lon: float = Query(...),
    provider: str = Query("openmeteo"),
    days: int = Query(10, ge=1, le=10),
) -> Dict[str, Any]:
    try:
        wx = get_weather_hourly(lat, lon, provider=provider, days=days)
        hourly = wx.get("hourly", {})
        times = hourly.get("time", [])
        t2m   = hourly.get("temperature_2m", [])
        rh2m  = hourly.get("relative_humidity_2m", [])
        n = min(len(times), len(t2m), len(rh2m))
        by_day: Dict[str, List[Dict[str, Any]]] = {}
        for i in range(n):
            d = _iso_date(times[i])
            hi = heat_index_c(t2m[i], rh2m[i])
            wb = wbgt_shade_c(t2m[i], rh2m[i])
            by_day.setdefault(d, []).append({"t": t2m[i], "hi": hi, "wb": wb})
        days_out = []
        for d in sorted(by_day.keys()):
            hrs = by_day[d]
            t_min = min(h["t"] for h in hrs)
            hi_max = max(h["hi"] for h in hrs)
            wb_max = max(h["wb"] for h in hrs)
            days_out.append({
                "date": d,
                "t_min_c": round(t_min, 1),
                "hi_max_c": round(hi_max, 1),
                "wbgt_max_c": round(wb_max, 1),
                "tier": tier_from_heat(hi_max, wb_max)
            })
        return {"ok": True, "provider": wx.get("provider"), "days": days_out}
    except WeatherProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Heat daily failed: {e}" )

