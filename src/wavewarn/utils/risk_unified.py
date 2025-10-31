# src/wavewarn/utils/risk_unified.py
from typing import Optional

# simple tier ordering
_ORDER = {"unknown": 0, "safe": 1, "caution": 2, "risk": 3, "extreme": 4}

def tier_to_score(tier: str) -> int:
    return _ORDER.get((tier or "unknown").lower(), 0) * 25  # 0,25,50,75,100

def combine_tiers(heat_tier: str, aqi_tier: str, w_heat: float = 0.6, w_aqi: float = 0.4) -> tuple[int, str]:
    """
    Weighted combo (default heat 60%, AQI 40%).
    Returns (score 0..100, tier str). Worst-tier guard: if either is 'extreme', cap tier to 'extreme'.
    """
    hs = tier_to_score(heat_tier)
    as_ = tier_to_score(aqi_tier)
    score = round(w_heat * hs + w_aqi * as_)
    # map back to tier
    if score >= 88 or heat_tier == "extreme" or aqi_tier == "extreme":
        tier = "extreme"
    elif score >= 63:
        tier = "risk"
    elif score >= 38:
        tier = "caution"
    elif score > 0:
        tier = "safe"
    else:
        tier = "unknown"
    return score, tier

