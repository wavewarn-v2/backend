"""
WaveWarn Model-backed Risk Routes (no collisions)
-------------------------------------------------
Returns RiskTimeline / RiskPoint using Open-Meteo hourly data.

Paths:
- /risk/model/live
- /risk/model/timeline
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict
import httpx
from datetime import datetime, timezone, timedelta
from ..models import RiskPoint, RiskTimeline

router = APIRouter(prefix="/risk/model", tags=["risk-model"])

# ---- simple placeholder scoring (replace with your ML later) ----
def score_hourly(temp_c: float | None, rh: float | None) -> int:
    if temp_c is None or rh is None:
        return 0
    s = (float(temp_c) * 2.0) + (float(rh) * 0.3) - 20
    s = 0 if s < 0 else (100 if s > 100 else s)
    return int(round(s))

def tier_from_score(score: int) -> str:
    if score >= 80: return "extreme"
    if score >= 60: return "high"
    if score >= 40: return "moderate"
    if score >= 20: return "caution"
    return "safe"

def drivers_from_score(score: int) -> Dict[str, float]:
    return {
        "heat_index": round(score * 0.60, 2),
        "humidity_load": round(score * 0.30, 2),
        "clear_sky_risk": round(score * 0.10, 2),
    }

# ---- Open-Meteo hourly fetch ----
def build_openmeteo_hourly_url(lat: float, lon: float, hours: int) -> str:
    days = max(1, min(16, (hours + 23) // 24))  # ceil(hours/24) in [1..16]
    return (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,cloud_cover"
        f"&forecast_days={days}&timezone=auto"
    )

def fetch_openmeteo_hourly(lat: float, lon: float, hours: int) -> dict:
    url = build_openmeteo_hourly_url(lat, lon, hours)
    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()

# ---- endpoints ----
@router.get("/live", response_model=dict)
def model_live_risk(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    try:
        js = fetch_openmeteo_hourly(lat, lon, hours=1)
        h = js.get("hourly", {})
        temps = h.get("temperature_2m", [])
        rhs   = h.get("relative_humidity_2m", [])
        t_now = temps[0] if temps else None
        rh_now = rhs[0] if rhs else None

        score = score_hourly(t_now, rh_now)
        tier = tier_from_score(score)
        drivers = drivers_from_score(score)

        return {
            "ok": True,
            "when": datetime.now(timezone.utc).isoformat(),
            "location": {"lat": lat, "lon": lon},
            "score": score,
            "tier": tier,
            "drivers": drivers,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo fetch/compute failed: {e}")

@router.get("/timeline", response_model=RiskTimeline)
def model_risk_timeline(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    hours: int = Query(24, ge=1, le=72, description="How many hours ahead"),
):
    try:
        js = fetch_openmeteo_hourly(lat, lon, hours=hours)
        h = js.get("hourly", {})
        temps = h.get("temperature_2m", [])
        rhs   = h.get("relative_humidity_2m", [])

        points: List[RiskPoint] = []
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        for i in range(min(hours, len(temps), len(rhs) if rhs else hours)):
            hour_local = (now + timedelta(hours=i)).hour
            s = score_hourly(temps[i] if i < len(temps) else None,
                             rhs[i]   if i < len(rhs)   else None)
            points.append(RiskPoint(
                hour=hour_local,
                score=int(s),
                tier=tier_from_score(s),
                drivers=drivers_from_score(s),
            ))
        return RiskTimeline(ok=True, location={"lat": lat, "lon": lon}, points=points)

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo fetch/compute failed: {e}")

