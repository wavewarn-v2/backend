from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import List, Dict

router = APIRouter()

@router.get("/risk/timeline")
def risk_timeline(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    hours: int = Query(24, ge=1, le=72, description="How many hours ahead")
) -> Dict:
    """
    Returns a stubbed 24–72h hourly risk forecast (0–100). Replace with real model later.
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 60 + 20  # 20–79
    out: List[Dict] = []
    for h in range(hours):
        hour = (now + timedelta(hours=h)).hour
        diurnal = 20 if 12 <= hour <= 16 else (10 if 10 <= hour <= 18 else 0)
        score = max(0, min(100, base + diurnal))
        out.append({
            "ts": int((now + timedelta(hours=h)).timestamp()),
            "score": score
        })

    return {"ok": True, "location": {"lat": lat, "lon": lon}, 
"points":out}
