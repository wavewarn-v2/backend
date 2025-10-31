# src/wavewarn/utils/aqi.py
# Minimal AQI computation for PM2.5 (µg/m3) and O3 (ppb) using US EPA breakpoints.

from typing import Optional

# PM2.5 breakpoints (µg/m3)
_PM25_BP = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]

# O3 (8-hr) breakpoints (ppb). If you only have 1-hr, this is still a rough proxy.
_O3_BP = [
    (0, 54, 0, 50),
    (55, 70, 51, 100),
    (71, 85, 101, 150),
    (86, 105, 151, 200),
    (106, 200, 201, 300),  # coarse upper bucket
]

def _interp_aqi(c: float, bp):
    for lo, hi, aqi_lo, aqi_hi in bp:
        if lo <= c <= hi:
            return round((aqi_hi - aqi_lo) * (c - lo) / (hi - lo) + aqi_lo)
    return None

def aqi_pm25(ugm3: Optional[float]) -> Optional[int]:
    if ugm3 is None:
        return None
    return _interp_aqi(float(ugm3), _PM25_BP)

def aqi_o3(ppb: Optional[float]) -> Optional[int]:
    if ppb is None:
        return None
    return _interp_aqi(float(ppb), _O3_BP)

def aqi_overall(pm25_ugm3: Optional[float], o3_ppb: Optional[float]) -> Optional[int]:
    a_pm = aqi_pm25(pm25_ugm3)
    a_o3 = aqi_o3(o3_ppb)
    vals = [v for v in (a_pm, a_o3) if v is not None]
    return max(vals) if vals else None

def aqi_tier(aqi: Optional[int]) -> str:
    if aqi is None: return "unknown"
    if aqi <= 50: return "good"
    if aqi <= 100: return "moderate"
    if aqi <= 150: return "unhealthy_for_sensitive"
    if aqi <= 200: return "unhealthy"
    if aqi <= 300: return "very_unhealthy"
    return "hazardous"

