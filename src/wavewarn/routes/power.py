from fastapi import APIRouter, Query, HTTPException
from ..utils.power_client import fetch_power_json, normalize_power, PowerError

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("/power")
def power(url: str = Query(..., description="Paste NASA POWER API URL")):
    try:
        js = fetch_power_json(url)
        rows = normalize_power(js)
        return {"rows": rows, "count": len(rows)}
    except PowerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

