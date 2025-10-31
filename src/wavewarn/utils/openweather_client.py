# src/wavewarn/utils/openweather_client.py
import os
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class OWMError(Exception):
    pass

def _get_api_key() -> str:
    api = os.getenv("OWM_API_KEY") or os.getenv("OPENWEATHER_API_KEY")
    if not api:
        raise OWMError("Missing OWM_API_KEY in environment (.env).")
    return api

def _iso_utc_from_unix(ts: int) -> str:
    # OpenWeather returns UNIX seconds (UTC)
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")

def fetch_onecall(lat: float, lon: float, *, units: str = "metric",
                  exclude: str = "minutely,alerts") -> Dict[str, Any]:
    """
    Calls OpenWeather One Call 3.0 API for a location.
    Returns raw JSON.
    """
    api = _get_api_key()
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api,
        "units": units,
        "exclude": exclude,  # we want current,hourly,daily by default
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 401:
            raise OWMError("OpenWeather: 401 Unauthorized (check API key & plan).")
        if r.status_code == 429:
            raise OWMError("OpenWeather: 429 Rate limit exceeded.")
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise OWMError(f"OpenWeather request failed: {e}") from e

def normalize_to_openmeteo_shape(onecall: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OpenWeather hourly/daily into an Open-Meteo–like shape.
    Produces keys we already use elsewhere: 'hourly' with arrays.
    """
    hourly = onecall.get("hourly", []) or []
    out_time: List[str] = []
    out_t2m: List[Optional[float]] = []
    out_rh:  List[Optional[float]] = []
    out_ws:  List[Optional[float]] = []

    for h in hourly:
        out_time.append(_iso_utc_from_unix(h.get("dt")))
        out_t2m.append(h.get("temp"))
        out_rh.append(h.get("humidity"))
        out_ws.append(h.get("wind_speed"))

    return {
        "hourly": {
            "time": out_time,
            "temperature_2m": out_t2m,
            "relative_humidity_2m": out_rh,
            "wind_speed_10m": out_ws,
        }
    }

def fetch_hourly(lat: float, lon: float, *, days: int = 2, hours: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience wrapper:
    - OpenWeather OneCall hourly horizon ~48h (depending on plan).
    - 'days' will be translated to hours=min(days*24, available).
    - If 'hours' provided, that takes precedence.
    Returns normalized dict from normalize_to_openmeteo_shape().
    """
    raw = fetch_onecall(lat, lon)
    norm = normalize_to_openmeteo_shape(raw)

    # Slice to requested hours if specified
    if hours is None:
        hours = min(len(norm["hourly"]["time"]), int(days) * 24)

    for key in ["time", "temperature_2m", "relative_humidity_2m", "wind_speed_10m"]:
        norm["hourly"][key] = norm["hourly"][key][:hours]

    return norm

