# src/wavewarn/routes/weather_openmeteo.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from ..utils.openmeteo_weather_client import fetch_weather_hourly, OMWeatherError

router = APIRouter(prefix="/sources/wx", tags=["sources-weather"])

@router.get("/openmeteo")
def wx_openmeteo(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(10, ge=1, le=10,
                      description="Hourly weather horizon (1–10 days)"),
    include_uv: bool = Query(True),
    include_apparent: bool = Query(True)
) -> Dict[str, Any]:
    """
    Returns HOURLY weather drivers for heat risk: T, RH, wind, (optional UV, apparent T).
    (UV/apparent are included by the client if present in API response; we pass them through.)
    """
    try:
        js = fetch_weather_hourly(lat, lon, days=days)
        hh = js.get("hourly", {})
        out: Dict[str, Any] = {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "hours": len(hh.get("time", []) or []),
            "timeline": {
                "time": hh.get("time", []),
                "temperature_2m": hh.get("temperature_2m", []),
                "relative_humidity_2m": hh.get("relative_humidity_2m", []),
                "wind_speed_10m": hh.get("wind_speed_10m", []),
            },
            "source": "Open-Meteo Weather"
        }
        # pass-through optional series if present
        if include_uv and "uv_index" in hh:
            out["timeline"]["uv_index"] = hh["uv_index"]
        if include_apparent and "apparent_temperature" in hh:
            out["timeline"]["apparent_temperature"] = hh["apparent_temperature"]
        return out
    except OMWeatherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo weather fetch failed: {e}")

