# src/wavewarn/routes/air_quality_openmeteo.py
from fastapi import APIRouter, Query, HTTPException
from ..utils.openmeteo_air_client import fetch_air_quality, OMAirError
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/sources/air", tags=["sources-air"])

@router.get("/openmeteo")
def air_openmeteo(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(5, ge=1, le=5, description="Air-quality forecast days (max 5)")
):
    try:
        js = fetch_air_quality(lat, lon, days=days)
        hh = js.get("hourly", {})
        times = hh.get("time", [])
        pm2  = hh.get("pm2_5", [])
        o3   = hh.get("ozone", [])

        points = []
        for t, p, o in zip(times, pm2, o3):
            o3_ppb = None if o is None else float(o) / 2.0  # µg/m³ → ~ppb
            tier = aqi_tier(aqi_overall(p, o3_ppb))
            points.append({"ts": t, "pm25": p, "o3_ppb": o3_ppb, "tier": tier})

        latest = points[-1] if points else None
        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "forecast_days": days,
            "latest": latest,
            "timeline": points,
            "source": "Open-Meteo Air Quality"
        }
    except OMAirError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo Air fetch failed: {e}")

