# src/wavewarn/utils/daily_reduce.py
from typing import List, Dict, Any
from collections import defaultdict

_ORDER = {"unknown": 0, "safe": 1, "caution": 2, "risk": 3, "extreme": 4}

def group_by_day(timeline: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_day: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in timeline:
        ts: str = row.get("ts") or ""
        day = ts[:10]  # 'YYYY-MM-DD'
        if day:
            by_day[day].append(row)
    return dict(by_day)

def reduce_day(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"score_max": None, "tier_max": "unknown"}
    # pick max combined score; break ties by worse tier
    best = max(rows, key=lambda r: (_ORDER.get(r["combined"]["tier"], 0), r["combined"]["score"] or 0))
    return {
        "score_max": best["combined"]["score"],
        "tier_max": best["combined"]["tier"]
    }

