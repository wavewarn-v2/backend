"""
WaveWarn Risk Routes
--------------------
Provides endpoints for real-time risk scoring and timeline stub.
"""

from fastapi import APIRouter, Query
from typing import List
from datetime import datetime
from ..models import RiskPoint, RiskTimeline
from ..utils.risk_calc import hourly_score, tier_from_score, 
drivers_from_score

router = APIRouter()


@router.get("/risk/live", response_model=dict)
def live_risk(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    Return a mock live risk score and related tier/drivers.
    """
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 100
    score = hourly_score(datetime.utcnow().hour, base)
    tier = tier_from_score(score)
    drivers = drivers_from_score(score)

    return {
        "ok": True,
        "location": {"lat": lat, "lon": lon},
        "score": score,
        "tier": tier,
        "drivers": drivers,
    }


@router.get("/risk/timeline", response_model=RiskTimeline)
def risk_timeline(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    Return a 24-hour hourly risk timeline (stubbed diurnal curve seeded by 
location).
    """
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 100
    points: List[RiskPoint] = []
    for h in range(24):
        s = hourly_score(h, base)
        points.append(RiskPoint(hour=h, score=s))

    return RiskTimeline(location={"lat": lat, "lon": lon}, points=points)



