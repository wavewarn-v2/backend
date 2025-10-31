# src/wavewarn/routes/openaq.py
import httpx
from fastapi import APIRouter, Query, HTTPException
from ..utils.openaq_v3_client import (
    get_locations_near, get_sensors_by_location, choose_sensor_for_params,
    get_location_latest, extract_pm25_o3_from_latest,
    get_sensor_hours, summarize_hours_to_latest, OpenAQV3Error
)
from ..utils.aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

router = APIRouter(prefix="/sources/openaq", tags=["sources-openaq"])

@router.get("/nearby")
def openaq_nearby(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_m: int = Query(10000, ge=1000, le=120000),
    expand_search: bool = Query(True),
    hours: int = Query(24, ge=1, le=168),
    max_locations: int = Query(8, ge=1, le=30)
):
    """
    v3-compliant flow with robust search:
      - filter locations that have pm25/o3
      - try up to N closest locations
      - for each: try /latest, else /sensors/{id}/hours
      - expand radius up to ~120km if needed
    """
    try:
        wanted = ["pm25", "o3"]
        tried_radii = []
        r = radius_m

        for _ in range(4 if expand_search else 1):  # up to 4 expansions
            locs = get_locations_near(lat, lon, radius_m=r, limit=max_locations)
            tried_radii.append(r)

            if not locs:
                r = int(r * 1.75)  # expand faster
                continue

            # iterate through several closest locations
            for loc in locs[:max_locations]:
                loc_id = loc["id"]
                station_name = loc.get("name")

                # A) try /latest
                pm25_val, o3_val = None, None
                try:
                    latest = get_location_latest(loc_id)
                    if latest:
                        pm25_val, o3_val, station_name = extract_pm25_o3_from_latest(latest)
                except Exception:
                    pass

                # B) fallback by sensor hours if latest had nothing
                if pm25_val is None and o3_val is None:
                    sensors = get_sensors_by_location(loc_id)
                    sensor = choose_sensor_for_params(sensors, wanted)
                    if sensor:
                        rows = get_sensor_hours(sensor["id"], hours=hours)
                        v, p = summarize_hours_to_latest(rows)
                        if p == "pm25": pm25_val = v
                        if p == "o3":   o3_val = v

                if pm25_val is None and o3_val is None:
                    continue  # try next location

                a_pm25 = aqi_pm25(pm25_val)
                a_o3   = aqi_o3(o3_val)
                a_all  = aqi_overall(pm25_val, o3_val)

                return {
                    "ok": True,
                    "location_query": {"lat": lat, "lon": lon},
                    "search_radii_tried_m": tried_radii,
                    "station": {"id": loc_id, "name": station_name},
                    "pm25_ugm3": pm25_val,
                    "o3_ppb": o3_val,
                    "aqi": {"pm25": a_pm25, "o3": a_o3, "overall": a_all, "tier": aqi_tier(a_all)}
                }

            # if none of the locations had values, expand and retry
            r = int(r * 1.75)

        return {
            "ok": False,
            "msg": "No PM2.5/O3 data available after iterating locations and expanding radius.",
            "search_radii_tried_m": tried_radii
        }

    except OpenAQV3Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAQ v3 fetch/compute failed: {e}")

