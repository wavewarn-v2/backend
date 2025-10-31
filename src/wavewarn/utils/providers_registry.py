# src/wavewarn/utils/providers_registry.py
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
import httpx

from .providers import normalize_open_meteo_hourly
from .aggregate import hourly_to_daily, score_risk, detect_heatwave
from .power_client import fetch_power_json, normalize_power  # safe even if POWER is disabled

RowD = Dict[str, Any]

def fetch_open_meteo_daily(lat: float, lon: float, days: int = 7) -> List[RowD]:
    """
    Primary provider: Open-Meteo (hourly → daily aggregation).
    Returns rows with keys: date, TMAX, TMIN, RH, WS, SW, CLD, SRC, risk_score, tier, heatwave_*.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,cloud_cover"
        f"&forecast_days={days}&timezone=auto"
    )
    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    hourly = normalize_open_meteo_hourly(r.json())
    daily = hourly_to_daily(hourly)
    daily = score_risk(daily)
    daily = detect_heatwave(daily)
    return daily

def try_power_daily(power_url: Optional[str]) -> Optional[List[RowD]]:
    """
    Optional provider: NASA POWER (already normalized by your adapter).
    Enabled only if ENABLE_POWER=1/true/yes AND a URL is provided.
    Returns None on any failure (caller can ignore).
    """
    if not power_url:
        return None
    if os.getenv("ENABLE_POWER", "0").lower() not in ("1", "true", "yes"):
        return None
    try:
        js = fetch_power_json(power_url)
        rows = normalize_power(js)
        return rows
    except Exception:
        return None  # fail-closed to keep the API stable

