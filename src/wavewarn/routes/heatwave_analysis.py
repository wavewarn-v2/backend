# src/wavewarn/routes/heatwave_analysis.py

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List

from .risk import (
    fetch_openmeteo_hourly,
    score_hourly,
    tier_from_score,
    drivers_from_score,
)

router = APIRouter(prefix="/heatwave", tags=["heatwave"])

_TIER_ORDER = {
    "unknown": 0,
    "safe": 1,
    "caution": 2,
    "moderate": 3,
    "high": 4,
    "extreme": 5,
}


def _is_heatwave_day(tier: str) -> bool:
    return _TIER_ORDER.get(tier, 0) >= _TIER_ORDER["high"]


def _severity_label(tier: str) -> str:
    if tier == "extreme":
        return "Extreme"
    if tier == "high":
        return "Severe"
    if tier == "moderate":
        return "Elevated"
    return "Normal"


def _status(active: bool, peak_tier: str | None) -> str:
    if not active:
        return "INACTIVE — No heatwave"

    return f"ACTIVE — {_severity_label(peak_tier or 'high')}"


def _insight(active: bool, duration_days: int) -> str:
    if not active:
        return "No heatwave expected"

    return f"{duration_days}-day elevated heat event"


def _recommendations(active: bool, peak_tier: str | None) -> List[str]:
    if not active:
        return [
            "Continue normal outdoor activity with basic hydration",
            "Monitor daily forecast updates",
            "Use shade during hot afternoon periods",
        ]

    if peak_tier == "extreme":
        return [
            "Avoid outdoor activity between 11 AM – 4 PM",
            "Stay hydrated throughout the day",
            "Wear lightweight, loose-fitting clothing",
            "Use sunscreen during daytime exposure",
            "Check vulnerable individuals regularly",
        ]

    return [
        "Limit outdoor activity between 11 AM – 4 PM",
        "Drink water regularly throughout the day",
        "Take breaks in shaded or cool areas",
        "Avoid strenuous outdoor work during peak heat",
        "Check elderly neighbours and vulnerable individuals",
    ]


def _find_spells(days: List[Dict[str, Any]], min_len: int = 3) -> List[Dict[str, Any]]:
    spells = []
    current = []

    for day in days:
        if _is_heatwave_day(day["tier"]):
            current.append(day)
        else:
            if len(current) >= min_len:
                spells.append(current)
            current = []

    if len(current) >= min_len:
        spells.append(current)

    spans = []

    for block in spells:
        peak = max(
            block,
            key=lambda d: (
                _TIER_ORDER.get(d.get("tier", "unknown"), 0),
                d.get("max_score", 0),
                d.get("avg_score", 0),
            ),
        )

        peak_hour = peak.get("peak_hour")

        spans.append({
            "start": block[0]["date"],
            "end": block[-1]["date"],
            "days": len(block),
            "peak": {
                "date": peak["date"],
                "tier": peak["tier"],
                "score": peak.get("max_score", peak.get("avg_score", 0)),
                "peak_hour": peak_hour,
            },
        })

    return spans


def _primary_span(spans: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not spans:
        return None

    return max(
        spans,
        key=lambda s: (
            s.get("days", 0),
            _TIER_ORDER.get(s.get("peak", {}).get("tier", "unknown"), 0),
            s.get("peak", {}).get("score", 0),
        ),
    )


def _narrative(
    active: bool,
    duration_days: int,
    peak_tier: str | None,
    peak_hour: int | None,
) -> str:
    if not active:
        return (
            "No sustained heatwave pattern is expected in the selected forecast window. "
            "Conditions may still vary by hour, so monitor daily risk updates."
        )

    severity = _severity_label(peak_tier or "high").lower()

    if peak_hour is not None:
        return (
            f"Persistent elevated heat risk is expected for {duration_days} days. "
            f"Peak stress is likely around {peak_hour}:00, with {severity} conditions during the hottest period."
        )

    return (
        f"Persistent elevated heat risk is expected for {duration_days} days. "
        f"{severity.title()} conditions may develop during the hottest periods."
    )


@router.get("/analysis/daily", response_model=dict)
def heatwave_analysis_daily(
    lat: float = Query(...),
    lon: float = Query(...),
    days: int = Query(10, ge=1, le=10),
) -> Dict[str, Any]:
    try:
        hours = days * 24

        js = fetch_openmeteo_hourly(lat, lon, hours=hours)
        h = js.get("hourly", {})

        times = h.get("time", [])
        temps = h.get("temperature_2m", [])
        rhs = h.get("relative_humidity_2m", [])
        winds = h.get("wind_speed_10m", [])
        radiation = h.get("shortwave_radiation", [])
        clouds = h.get("cloud_cover", [])

        total = min(hours, len(times), len(temps), len(rhs))

        day_map: Dict[str, List[Dict[str, Any]]] = {}

        for i in range(total):
            time_value = times[i]
            date_part = time_value.split("T")[0]
            hour_part = int(time_value.split("T")[1].split(":")[0])

            temp = temps[i] if i < len(temps) else None
            rh = rhs[i] if i < len(rhs) else None
            wind = winds[i] if i < len(winds) else 0
            rad = radiation[i] if i < len(radiation) else 0
            cloud = clouds[i] if i < len(clouds) else 0

            score = score_hourly(temp, rh)
            tier = tier_from_score(score)

            point = {
                "hour": hour_part,
                "temperature_c": temp,
                "humidity_percent": rh,
                "wind_speed_kmh": wind,
                "solar_radiation": rad,
                "cloud_cover_percent": cloud,
                "score": score,
                "tier": tier,
                "drivers": drivers_from_score(score),
            }

            day_map.setdefault(date_part, []).append(point)

        daily_days = []

        for date, hourly in day_map.items():
            scores = [x["score"] for x in hourly]
            temps_day = [
                x["temperature_c"]
                for x in hourly
                if x["temperature_c"] is not None
            ]

            avg_score = round(sum(scores) / len(scores), 2) if scores else 0
            max_score = max(scores) if scores else 0
            min_score = min(scores) if scores else 0

            max_temp = max(temps_day) if temps_day else None
            min_temp = min(temps_day) if temps_day else None

            peak_hour = (
                max(hourly, key=lambda x: x["score"])["hour"]
                if hourly
                else None
            )

            daily_days.append({
                "date": date,
                "tier": tier_from_score(int(avg_score)),
                "avg_score": avg_score,
                "max_score": max_score,
                "min_score": min_score,
                "max_temperature_c": max_temp,
                "min_temperature_c": min_temp,
                "peak_hour": peak_hour,
            })

        heatwave_spans = _find_spells(daily_days, min_len=3)
        primary = _primary_span(heatwave_spans)

        heatwave_active = primary is not None
        duration_days = primary.get("days", 0) if primary else 0
        peak = primary.get("peak", {}) if primary else {}
        peak_tier = peak.get("tier") if peak else None
        peak_hour = peak.get("peak_hour") if peak else None

        return {
            "ok": True,
            "location": {
                "lat": lat,
                "lon": lon,
            },
            "days_requested": days,
            "days": daily_days,
            "heatwave_spans": heatwave_spans,
            "primary_span": primary,
            "heatwave_active": heatwave_active,
            "insight": _insight(heatwave_active, duration_days),
            "status": _status(heatwave_active, peak_tier),
            "narrative": _narrative(
                heatwave_active,
                duration_days,
                peak_tier,
                peak_hour,
            ),
            "duration_days": duration_days,
            "peak_severity": _severity_label(peak_tier) if peak_tier else None,
            "peak_hour": peak_hour,
            "recommendations": _recommendations(heatwave_active, peak_tier),
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Heatwave analysis failed: {e}",
        )
