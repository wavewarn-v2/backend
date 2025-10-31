# src/wavewarn/utils/openaq_v3_client.py
from typing import Dict, Any, List, Optional, Tuple
import os
import httpx
import certifi
from datetime import datetime, timedelta, timezone

class OpenAQV3Error(Exception):
    pass

def _headers() -> Dict[str, str]:
    api_key = os.getenv("OPENAQ_API_KEY")
    if not api_key:
        raise OpenAQV3Error("OPENAQ_API_KEY not set (export it or load via .env).")
    return {"Accept": "application/json", "X-API-Key": api_key}

def _client() -> httpx.Client:
    ca_path = os.getenv("OPENAQ_CA_BUNDLE") or certifi.where()
    return httpx.Client(timeout=30.0, verify=ca_path)

# ---------- discovery ----------
def get_locations_near(lat: float, lon: float, radius_m: int = 15000, limit: int = 30) -> List[Dict[str, Any]]:
    # Filter for locations that actually measure pm25 or o3
    url = (
        f"https://api.openaq.org/v3/locations?"
        f"coordinates={lat},{lon}&radius={radius_m}&limit={limit}&sort=distance"
        f"&parameters=pm25,o3"
    )
    with _client() as c:
        r = c.get(url, headers=_headers())
    r.raise_for_status()
    return r.json().get("results", [])

def get_sensors_by_location(location_id: int) -> List[Dict[str, Any]]:
    url = f"https://api.openaq.org/v3/locations/{location_id}/sensors"
    with _client() as c:
        r = c.get(url, headers=_headers())
    r.raise_for_status()
    return r.json().get("results", [])

def choose_sensor_for_params(sensors: List[Dict[str, Any]], wanted: List[str]) -> Optional[Dict[str, Any]]:
    # Prefer pm25, then o3
    by_param = {}
    for s in sensors:
        p = (s.get("parameter") or {}).get("name")
        if p:
            by_param.setdefault(p, s)
    for w in wanted:
        if w in by_param:
            return by_param[w]
    return sensors[0] if sensors else None

# ---------- latest-at-location (shortcut) ----------
def get_location_latest(location_id: int) -> Dict[str, Any]:
    url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
    with _client() as c:
        r = c.get(url, headers=_headers())
    r.raise_for_status()
    js = r.json()
    results = js.get("results") or []
    return results[0] if results else {}

def extract_pm25_o3_from_latest(latest: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    name = latest.get("name")
    measurements = latest.get("measurements", [])
    pm25, o3_ppb = None, None

    def _to_ppb_o3(val: float, units: str) -> float:
        u = (units or "").lower().strip()
        if u == "ppb": return float(val)
        if u == "ppm": return float(val) * 1000.0
        return float(val) / 2.0  # assume µg/m³ → ~ppb

    for m in measurements:
        p = (m.get("parameter") or {}).get("name")
        val = m.get("value")
        units = (m.get("parameter") or {}).get("units", "")
        if val is None: 
            continue
        if p == "pm25":
            pm25 = float(val)
        elif p == "o3":
            o3_ppb = _to_ppb_o3(float(val), units)
    return pm25, o3_ppb, name

# ---------- sensor time-series ----------
def get_sensor_hours(sensor_id: int, hours: int = 24) -> List[Dict[str, Any]]:
    dt_to = datetime.now(timezone.utc)
    dt_from = dt_to - timedelta(hours=hours)
    qs = (f"?datetime_from={dt_from.strftime('%Y-%m-%dT%H:%M:%SZ')}"
          f"&datetime_to={dt_to.strftime('%Y-%m-%dT%H:%M:%SZ')}"
          f"&limit=500")
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours{qs}"
    with _client() as c:
        r = c.get(url, headers=_headers())
    r.raise_for_status()
    return r.json().get("results", [])

def summarize_hours_to_latest(results: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str]]:
    # pick the first (most recent) non-null
    for row in results:
        val = row.get("value")
        param = (row.get("parameter") or {}).get("name")
        if val is not None and param:
            return float(val), param
    return None, None

