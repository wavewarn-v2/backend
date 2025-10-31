from fastapi import APIRouter, Query, HTTPException
import httpx
from ..utils.providers import normalize_open_meteo_hourly
from ..utils.aggregate import hourly_to_daily, score_risk, detect_heatwave

router = APIRouter(prefix="/sources")

@router.get("/openmeteo-hourly")
def openmeteo_hourly(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(7, ge=1, le=16),
    include_hourly: bool = Query(False)
):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,cloud_cover"
        f"&forecast_days={days}&timezone=auto"
    )
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.get(url, headers={"Accept":"application/json"})
        r.raise_for_status()
        hourly_rows = normalize_open_meteo_hourly(r.json())
        daily_rows  = hourly_to_daily(hourly_rows)
        daily_rows  = score_risk(daily_rows)
        daily_rows  = detect_heatwave(daily_rows)
        resp = {"ok": True, "daily": daily_rows, "daily_count": len(daily_rows)}
        if include_hourly:
            resp["hourly"] = hourly_rows
            resp["hourly_count"] = len(hourly_rows)
        return resp
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo hourly fetch/parse failed: {e}")

