# src/wavewarn/routes/waqi.py
from fastapi import APIRouter, Query, HTTPException
from ..utils.waqi_client import fetch_geo, extract_latest, WAQIError
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/sources/aq", tags=["sources-air"])

@router.get("/waqi")
def waqi_nearby(
    lat: float = Query(...),
    lon: float = Query(...)
):
    """
    Current AQ near a point, from WAQI geo feed (token required).
    Returns raw WAQI AQI plus our computed PM2.5/O3 AQI and tier.
    """
    try:
        data = fetch_geo(lat, lon)
        latest = extract_latest(data)

        pm25 = latest["pm25"]     # µg/m³
        o3ppb = latest["o3"]      # WAQI o3 is usually ppb-equivalent (varies by station)
        a_pm = aqi_pm25(pm25)
        a_o3 = aqi_o3(o3ppb)
        a_all = aqi_overall(pm25, o3ppb)

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "station": latest["station"],
            "ts": latest["ts"],
            "waqi_aqi": latest["aqi"],     # WAQI’s own composite index (0–500)
            "pm25_ugm3": pm25,
            "o3_ppb": o3ppb,
            "aqi": {
                "pm25": a_pm,
                "o3": a_o3,
                "overall": a_all,
                "tier": aqi_tier(a_all)
            },
            "source": "WAQI"
        }
    except WAQIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WAQI fetch failed: {e}")

