import httpx

class PowerError(Exception):
    pass

def fetch_power_json(url: str):
    """Fetch daily NASA POWER JSON data."""
    if not url.startswith("https://power.larc.nasa.gov/"):
        raise PowerError("Invalid NASA POWER URL.")
    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()

def normalize_power(js):
    """Convert NASA POWER JSON into clean daily rows."""
    params = js["properties"]["parameter"]
    dates = sorted(next(iter(params.values())).keys())
    rows = []
    for d in dates:
        row = {
            "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            "TMAX": params.get("T2M_MAX", {}).get(d),
            "TMIN": params.get("T2M_MIN", {}).get(d),
            "RH":   params.get("RH2M", {}).get(d),
            "WS":   params.get("WS2M", {}).get(d),
            "SW":   params.get("ALLSKY_SFC_SW_DWN", {}).get(d),
            "SRC":  "POWER"
        }
        tmax, rh = row["TMAX"], row["RH"]
        if tmax is not None and rh is not None:
            score = min(100, max(0, (float(tmax)*2.0) + (float(rh)*0.3) - 20))
            tier = ("low" if score < 40 else
                    "moderate" if score < 60 else
                    "high" if score < 80 else
                    "extreme")
            row["risk_score"] = round(score, 1)
            row["tier"] = tier
        else:
            row["risk_score"] = None
            row["tier"] = "unknown"
        rows.append(row)
    return rows

