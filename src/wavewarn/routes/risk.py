from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

router = APIRouter()

@router.get("/live-risk")
def live_risk(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    ts: Optional[int] = Query(None, description="Unix timestamp (seconds)")
):
    """
    Simple risk score generator based on location (stub).
    """
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 100
    score = max(0, min(100, base))
    if score >= 75:
        tier = "extreme"
    elif score >= 50:
        tier = "risk"
    elif score >= 25:
        tier = "caution"
    else:
        tier = "safe"

    now_iso = (datetime.utcfromtimestamp(ts) if ts else datetime.utcnow()).isoformat() + "Z"

    return {
        "ok": True,
        "when": now_iso,
        "location": {"lat": lat, "lon": lon},
        "score": score,
        "tier": tier,
        "drivers": {
            "heat_index": 0.6 * score,
            "wbgt": 0.5 * score,
            "lst_anomaly": 0.2 * score
        },
    }
