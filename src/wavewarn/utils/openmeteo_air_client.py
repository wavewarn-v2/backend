# src/wavewarn/utils/openmeteo_air_client.py
from typing import Dict, Any
import httpx
from .cache import aq_cache

class OMAirError(Exception): ...

def _ck(lat: float, lon: float, days: int) -> str:
    return f"om_air:{round(lat, 2)}:{round(lon, 2)}:d{days}"

def fetch_air_quality(lat: float, lon: float, days: int = 5) -> Dict[str, Any]:
    ck = _ck(lat, lon, days)
    cached = aq_cache.get(ck)
    if cached:
        return cached

    url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=pm2_5,ozone"
        f"&forecast_days={days}&timezone=auto"
    )
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        js = r.json()
        aq_cache.set(ck, js)     # <- cache for 1 hour
        return js
    except Exception as e:
        raise OMAirError(f"Open-Meteo air failed: {e}")

