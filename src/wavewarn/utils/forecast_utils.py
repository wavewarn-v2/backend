# src/wavewarn/utils/forecast_utils.py
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime

def group_hourly_to_daily(times: List[str], values: List[Optional[float]]) -> Dict[str, List[float]]:
    """
    Group hourly series into {YYYY-MM-DD: [values...]} (drops None).
    """
    by_day: Dict[str, List[float]] = defaultdict(list)
    for t, v in zip(times, values):
        if v is None:
            continue
        day = t[:10]  # 'YYYY-MM-DD'
        by_day[day].append(float(v))
    return by_day

def daily_mean(series_by_day: Dict[str, List[float]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for d, arr in series_by_day.items():
        out[d] = (sum(arr) / len(arr)) if arr else None
    return out

def daily_max(series_by_day: Dict[str, List[float]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for d, arr in series_by_day.items():
        out[d] = max(arr) if arr else None
    return out

def decay_extrapolate(last_value: Optional[float], n_days: int, half_life_days: float = 3.0) -> List[Optional[float]]:
    """
    Exponential decay from last_value across n_days.
    Returns list of length n_days (Day+1..Day+n).
    """
    if last_value is None:
        return [None] * n_days
    lam = 0.69314718056 / max(0.5, half_life_days)  # ln(2)/half_life
    vals: List[float] = []
    for k in range(1, n_days + 1):
        vals.append(last_value * (2.71828182846 ** (-lam * k)))
    return vals

