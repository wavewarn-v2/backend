# src/wavewarn/routes/timeline.py
from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

router = APIRouter()

@router.get("/risk/timeline")
def risk_timeline(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    hours: int = Query(24, ge=1, le=72, description="How many hours ahead") 
) -> Dict[str, Any]:
    """
    Returns a stubbed 24–72h hourly risk forecast (0–100).
    Diurnal bump mid-day to mimic hotter afternoons.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, 
microsecond=0)
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 60 + 20

    points: List[Dict[str, int]] = []
    for h in range(hours):
        cur = now + timedelta(hours=h)
        hour = cur.hour
        diurnal = 20 if 12 <= hour <= 16 else (10 if 10 <= hour <= 18 else 
0)
        score = max(0, min(100, base + diurnal))
        points.append({
            "ts": int(cur.timestamp()),
            "score": score
        })

    return {
        "ok": True,
        "location": {"lat": lat, "lon": lon},
        "points": points,
        "timeline": points
    }



