# src/wavewarn/utils/waqi_client.py
from typing import Dict, Any, Optional
import os
import httpx

class WAQIError(Exception):
    pass

def _token() -> str:
    tok = os.getenv("WAQI_TOKEN")
    if not tok:
        raise WAQIError("WAQI_TOKEN not set (put it in .env)")
    return tok

def fetch_geo(lat: float, lon: float) -> Dict[str, Any]:
    """
    Geo feed: current AQI + pollutants near given coords.
    Docs: https://aqicn.org/json-api/doc/
    """
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={_token()}"
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    js = r.json()
    if js.get("status") != "ok":
        raise WAQIError(f"WAQI returned status={js.get('status')}, data={js.get('data')}")
    return js["data"]

def extract_latest(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a few useful fields:
      - aqi (overall), city name, time
      - iaqi subfields: pm25, pm10, o3, no2, so2, co (if present)
    """
    iaqi = data.get("iaqi") or {}
    def _val(key: str) -> Optional[float]:
        v = iaqi.get(key)
        if isinstance(v, dict):
            v = v.get("v")
        return float(v) if v is not None else None

    return {
        "station": (data.get("city") or {}).get("name"),
        "ts": (data.get("time") or {}).get("iso") or data.get("time"),
        "aqi": data.get("aqi"),
        "pm25": _val("pm25"),
        "pm10": _val("pm10"),
        "o3": _val("o3"),
        "no2": _val("no2"),
        "so2": _val("so2"),
        "co": _val("co"),
    }

