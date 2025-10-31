# src/wavewarn/routes/weather_provider.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, Optional
from ..utils.weather_provider import get_hourly_weather, WeatherProviderError

router = APIRouter(prefix="/sources/wx", tags=["sources-weather"])

@router.get("/provider")
def wx_provider(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(10, ge=1, le=10),
    prefer: Optional[str] = Query(None, description="None | openmeteo | openweather")
) -> Dict[str, Any]:
    try:
        js = get_hourly_weather(lat, lon, days=days, prefer=prefer)
        hh = js.get("hourly", {}) or {}
        return {
            "ok": True,
            "provider": js.get("provider"),
            "hours": len(hh.get("time", []) or []),
            "timeline": hh
        }
    except WeatherProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

