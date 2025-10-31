from typing import List, Dict, Any
from collections import defaultdict

RowH = Dict[str, Any]
RowD = Dict[str, Any]

def hourly_to_daily(hourly: List[RowH]) -> List[RowD]:
    bin = defaultdict(lambda: {"T": [], "RH": [], "WS": [], "SW": [], "CLD": []})
    for r in hourly:
        day = r["time"][:10]
        if r.get("T")  is not None:  bin[day]["T"].append(float(r["T"]))
        if r.get("RH") is not None:  bin[day]["RH"].append(float(r["RH"]))
        if r.get("WS") is not None:  bin[day]["WS"].append(float(r["WS"]))
        if r.get("SW") is not None:  bin[day]["SW"].append(float(r["SW"]))
        if r.get("CLD") is not None: bin[day]["CLD"].append(float(r["CLD"]))
    out: List[RowD] = []
    for day in sorted(bin.keys()):
        B = bin[day]
        out.append({
            "date": day,
            "TMAX": max(B["T"])  if B["T"]  else None,
            "TMIN": min(B["T"])  if B["T"]  else None,
            "RH":   sum(B["RH"]) / len(B["RH"]) if B["RH"] else None,
            "WS":   max(B["WS"]) if B["WS"] else None,
            "SW":   sum(B["SW"]) if B["SW"] else None,
            "CLD":  sum(B["CLD"]) / len(B["CLD"]) if B["CLD"] else None,
            "SRC":  "OPEN-METEO(HOURLY)",
        })
    return out

def score_risk(rows: List[RowD]) -> List[RowD]:
    for r in rows:
        tmax, rh = r.get("TMAX"), r.get("RH")
        if tmax is not None and rh is not None:
            score = min(100, max(0, (float(tmax)*2.0) + (float(rh)*0.3) - 20))
            tier = ("low" if score < 40 else
                    "moderate" if score < 60 else
                    "high" if score < 80 else
                    "extreme")
            r["risk_score"] = round(score, 1)
            r["tier"] = tier
        else:
            r["risk_score"] = None
            r["tier"] = "unknown"
    return rows

def detect_heatwave(rows: List[RowD], abs_hot: float = 40.0, persistence_days: int = 2) -> List[RowD]:
    consec = 0
    for r in rows:
        hot = (r.get("TMAX") is not None and float(r["TMAX"]) >= abs_hot)
        r["heatwave_flag"] = bool(hot)
        if hot:
            consec += 1
        else:
            consec = 0
        r["heatwave_persistent"] = (consec >= persistence_days)
    return rows

