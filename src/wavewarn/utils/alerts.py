# src/wavewarn/utils/alerts.py
from typing import List, Dict, Any

_TIER_RANK = {"unknown":0, "safe":1, "caution":2, "risk":3, "extreme":4}

def first_window_at_or_above(timeline: List[Dict[str, Any]], min_tier: str = "risk", needed_hours: int = 3):
    """
    Return the first contiguous window (start_idx, end_idx) where combined.tier >= min_tier
    holds for at least needed_hours. timeline entries must have keys: "ts" and "combined":{"tier": ...}
    """
    thresh = _TIER_RANK.get(min_tier, 3)
    run_start = None
    for i, row in enumerate(timeline):
        tier = row.get("combined", {}).get("tier", "unknown")
        ok = _TIER_RANK.get(tier, 0) >= thresh
        if ok and run_start is None:
            run_start = i
        if not ok and run_start is not None:
            if i - run_start >= needed_hours:
                return run_start, i - 1
            run_start = None
    # tail run
    if run_start is not None and len(timeline) - run_start >= needed_hours:
        return run_start, len(timeline) - 1
    return None

