from typing import List, Dict, Any
RowH = Dict[str, Any]  # {"time","T","RH","WS","SW","CLD","SRC"}

def normalize_open_meteo_hourly(js: dict) -> List[RowH]:
    d = js["hourly"]
    times = d["time"]
    out: List[RowH] = []

    def gx(name, i):
        arr = d.get(name)
        return None if (arr is None or i >= len(arr)) else arr[i]

    for i, t in enumerate(times):
        out.append({
            "time": t,
            "T":   gx("temperature_2m", i),
            "RH":  gx("relative_humidity_2m", i),
            "WS":  gx("wind_speed_10m", i),
            "SW":  gx("shortwave_radiation", i),
            "CLD": gx("cloud_cover", i),
            "SRC": "OPEN-METEO(HOURLY)",
        })
    return out

