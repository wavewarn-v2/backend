# src/wavewarn/routes/live_risk.py
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone

router = APIRouter()

@router.get("/live-risk")
def live_risk(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    ts: Optional[int] = Query(None, description="Unix timestamp (seconds)")
):
    """
    Simple stub risk score based on location. Replace with real model later.
    """
    # stable pseudo-score from lat/lon
    base = (abs(int(lat * 10)) + abs(int(lon * 10))) % 100
    score = max(0, min(100, base))

    # Use explicit branches to avoid multi-line ternary issues
    if score >= 75:
        tier = "extreme"
    elif score >= 50:
        tier = "risk"
    elif score >= 25:
        tier = "caution"
    else:
        tier = "safe"

    when = (datetime.fromtimestamp(ts, tz=timezone.utc) if ts
            else datetime.now(timezone.utc)).isoformat()

    return {
        "ok": True,
        "when": when,
        "location": {"lat": lat, "lon": lon},
        "score": score,
        "tier": tier,
        "drivers": {
            "heat_index": round(0.6 * score, 2),
            "wbgt": round(0.5 * score, 2),
            "lst_anomaly": round(0.2 * score, 2),
        },
    }

