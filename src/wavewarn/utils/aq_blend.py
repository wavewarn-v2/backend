# src/wavewarn/utils/aq_blend.py
from typing import Optional, Dict, Any
from .aqi import aqi_pm25, aqi_o3, aqi_overall, aqi_tier

def make_aqi_from_pm25_o3(pm25_ugm3: Optional[float], o3_ppb: Optional[float]) -> Dict[str, Any]:
    a_pm = aqi_pm25(pm25_ugm3)
    a_o3 = aqi_o3(o3_ppb)
    a_all = aqi_overall(pm25_ugm3, o3_ppb)
    return {"pm25": a_pm, "o3": a_o3, "overall": a_all, "tier": aqi_tier(a_all)}

def blend_day1_with_waqi(day1_row: Dict[str, Any], waqi_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace Day 1 AQ fields/tier/score from WAQI if present.
    day1_row schema = {"date","score","tier","confidence"}
    waqi_payload schema = {"pm25_ugm3","o3_ppb","aqi":{...}}
    Returns a NEW dict (does not mutate input).
    """
    pm25 = waqi_payload.get("pm25_ugm3")
    o3ppb = waqi_payload.get("o3_ppb")

    # Recompute AQI bundle (our scale) from WAQI values
    aqi_bundle = make_aqi_from_pm25_o3(pm25, o3ppb)
    # Map to "score": use overall AQI (0..500) → scale to 0..100 for consistency
    # You can change this mapping later; for now simple linear clamp
    overall_0_500 = aqi_bundle["overall"] or 0
    score_0_100 = max(0, min(100, round(overall_0_500 * 0.2)))

    return {
        **day1_row,
        "score": score_0_100,
        "tier": aqi_bundle["tier"],
        "confidence": "high (live WAQI)"
    }
		
