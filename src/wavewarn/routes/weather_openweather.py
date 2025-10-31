# src/wavewarn/routes/weather_openweather.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, Optional
from ..utils.openweather_client import fetch_onecall, normalize_to_openmeteo_shape, fetch_hourly, OWMError

router = APIRouter(prefix="/sources/openweather", tags=["sources-openweather"])

@router.get("/onecall/raw")
def owm_onecall_raw(
    lat: float = Query(...),
    lon: float = Query(...),
    exclude: str = Query("minutely,alerts"),
    units: str = Query("metric"),
) -> Dict[str, Any]:
    try:
        data = fetch_onecall(lat, lon, units=units, exclude=exclude)
        return {"ok": True, "location": {"lat": lat, "lon": lon}, "raw": data}
    except OWMError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/hourly/normalized")
def owm_hourly_normalized(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(2, ge=1, le=2, description="OWM hourly horizon ~48h on free tiers"),
    hours: Optional[int] = Query(None, ge=1, le=48),
) -> Dict[str, Any]:
    try:
        data = fetch_hourly(lat, lon, days=days, hours=hours)
        return {"ok": True, "provider": "openweather", **data}
    except OWMError as e:
        raise HTTPException(status_code=400, detail=str(e))

