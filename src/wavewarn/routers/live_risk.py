from fastapi import APIRouter, Query
router = APIRouter()

@router.get("/live-risk")
def live_risk(lat: float = Query(...), lon: float = Query(...)):
    return {"score": 42, "tier": "Caution",
            "drivers": {"wbgt": 30.5, "hi": 37.2, "anomaly": 3.4, "wind": 1.2, "solar": 820, "persistence": 2}}
