# src/wavewarn/routes/forecast_air_hourly.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from ..utils.openmeteo_air_client import fetch_air_quality, OMAirError
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/forecast/air", tags=["forecast"])

@router.get("/hourly")
def air_forecast_hourly(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(5, ge=1, le=5, description="Hourly air-quality horizon (max 5)")
) -> Dict[str, Any]:
    """
    Returns HOURLY PM2.5/O3 for the next N days (N<=5) from Open-Meteo Air Quality,
    plus precomputed risk tier per hour for easy charting.
    """
    try:
        js = fetch_air_quality(lat, lon, days=days)  # clamps to <=5 in the client
        hh = js.get("hourly", {})
        times: List[str] = hh.get("time", []) or []
        pm2:  List[Optional[float]] = hh.get("pm2_5", []) or []
        o3ug: List[Optional[float]] = hh.get("ozone", []) or []

        points: List[Dict[str, Any]] = []
        for t, p, o_ug in zip(times, pm2, o3ug):
            o_ppb = None if o_ug is None else float(o_ug) / 2.0  # µg/m³ → ≈ ppb
            a_all = aqi_overall(p, o_ppb)
            points.append({
                "ts": t,
                "pm25_ugm3": p,
                "o3_ppb": o_ppb,
                "aqi_overall": a_all,
                "tier": aqi_tier(a_all)
            })

        # quick convenience stats (last hour + max over window)
        latest = points[-1] if points else None
        max_point = max(points, key=lambda r: (r["aqi_overall"] or -1)) if points else None

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "hours": len(points),
            "latest": latest,
            "max_hour": max_point,
            "timeline": points,
            "source": "Open-Meteo Air Quality"
        }
    except OMAirError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Air hourly fetch failed: {e}")

