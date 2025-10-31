# src/wavewarn/routes/heatwave_analysis.py
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from datetime import datetime

# Option A (preferred): use your unified daily (heat + AQI + optional WAQI override)
from .risk_unified_daily import unified_daily as _unified_daily

router = APIRouter(prefix="/heatwave", tags=["heatwave"])

# Tiers ordering used across project
_TIER_ORDER = {"unknown": 0, "safe": 1, "caution": 2, "risk": 3, "extreme": 4}

def _is_heatwave_day(tier: str) -> bool:
    return _TIER_ORDER.get(tier, 0) >= _TIER_ORDER["risk"]

def _find_spells(days: List[Dict[str, Any]], min_len: int = 3) -> List[Dict[str, Any]]:
    spells = []
    cur = []
    for d in days:
        if _is_heatwave_day(d["tier"]):
            cur.append(d)
        else:
            if len(cur) >= min_len:
                spells.append(cur)
            cur = []
    if len(cur) >= min_len:
        spells.append(cur)

    spans = []
    for block in spells:
        start = block[0]["date"]
        end   = block[-1]["date"]
        peak  = max(block, key=lambda r: (_TIER_ORDER[r["tier"]], r.get("score", 0)))
        spans.append({
            "start": start,
            "end": end,
            "days": len(block),
            "peak": {"tier": peak["tier"], "score": peak.get("score")},
        })
    return spans

def _narrative(spans: List[Dict[str, Any]]) -> str:
    if not spans:
        return "No heatwave (≥3 consecutive days of risk/extreme) expected in the next 10 days."
    parts = []
    for s in spans:
        parts.append(
            f"Heatwave from {s['start']} to {s['end']} "
            f"({s['days']} days), peak {s['peak']['tier']}."
        )
    return " ".join(parts)

@router.get("/analysis/daily")
def heatwave_analysis_daily(
    lat: float = Query(...),
    lon: float = Query(...),
    days_hourly: int = Query(5, ge=1, le=5, description="Hourly fusion base (1–5)"),
    extend_days: int = Query(5, ge=0, le=5, description="Extrapolated tail (0–5)"),
    use_waqi_day1: bool = Query(True),
    w_heat: float = Query(0.6, ge=0.0, le=1.0),
    w_aqi:  float = Query(0.4, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    10-day Heatwave Analysis:
      - Uses /risk/unified/daily under the hood (heat + AQI; optional Day1 WAQI override).
      - Detects heatwave spells (>= 3 consecutive days of tier >= risk).
      - Returns daily table, spells, and a narrative.
    """
    try:
        uni = _unified_daily(
            lat=lat, lon=lon,
            days_hourly=days_hourly,
            extend_days=extend_days,
            w_heat=w_heat, w_aqi=w_aqi,
            use_waqi_day1=use_waqi_day1,
        )
        if not isinstance(uni, dict) or not uni.get("ok"):
            raise HTTPException(status_code=502, detail="Unified daily upstream failed")

        days: List[Dict[str, Any]] = uni.get("days", [])
        spells = _find_spells(days, min_len=3)
        story  = _narrative(spells)

        return {
            "ok": True,
            "location": {"lat": lat, "lon": lon},
            "params": {
                "days_hourly": days_hourly, "extend_days": extend_days,
                "weights": {"heat": w_heat, "aqi": w_aqi},
                "use_waqi_day1": use_waqi_day1
            },
            "days": days,
            "heatwave_spans": spells,
            "narrative": story
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Heatwave analysis failed: {e}")

