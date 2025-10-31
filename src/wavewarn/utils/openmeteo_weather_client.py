# src/wavewarn/utils/openmeteo_weather_client.py
from typing import Dict, Any
import httpx
from .cache import wx_cache

class OMWeatherError(Exception): ...
# existing helper(s) you already have remain unchanged

def _ck(lat: float, lon: float, days: int) -> str:
    # round to ~1km buckets to improve cache hit rate
    return f"om_wx:{round(lat, 2)}:{round(lon, 2)}:d{days}"

def fetch_weather_hourly(lat: float, lon: float, days: int = 10) -> Dict[str, Any]:
    ck = _ck(lat, lon, days)
    cached = wx_cache.get(ck)
    if cached:
        return cached

    # your existing URL building logic (unchanged)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,uv_index,apparent_temperature"
        f"&forecast_days={days}&timezone=auto"
    )
    try:
        with httpx.Client(timeout=30.0) as c:
            r = c.get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        js = r.json()
        wx_cache.set(ck, js)     # <- cache for 1 hour (as configured)
        return js
    except Exception as e:
        raise OMWeatherError(f"Open-Meteo weather failed: {e}")

