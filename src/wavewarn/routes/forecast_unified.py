# src/wavewarn/routes/forecast_unified.py
from fastapi import APIRouter, Query
from typing import Optional
from ..utils.providers_registry import fetch_open_meteo_daily, try_power_daily

router = APIRouter(prefix="/forecast", tags=["forecast"])

@router.get("/daily")
def daily_forecast(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(7, ge=1, le=16, description="Forecast days (1–16)"),
    power_url: Optional[str] = Query(None, description="Optional NASA POWER daily URL")
):
    """
    Unified daily forecast:
      - primary rows from Open-Meteo (hourly→daily, with risk & heatwave flags)
      - optional POWER rows included if ENABLE_POWER and power_url provided
    """
    om_rows = fetch_open_meteo_daily(lat, lon, days)
    pow_rows = try_power_daily(power_url)

    return {
        "ok": True,
        "primary": "OPEN-METEO(HOURLY→DAILY)",
        "rows": om_rows,
        "power_rows": pow_rows or [],
        "fallback_used": bool(pow_rows),
    }

