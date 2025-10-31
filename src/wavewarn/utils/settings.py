# src/wavewarn/utils/settings.py
from dataclasses import dataclass, asdict
import os
from typing import Dict, Any

@dataclass
class RuntimeConfig:
    weather_provider_prefer: str = os.getenv("WEATHER_PROVIDER_PREFER", "auto")  # auto|openmeteo|openweather
    weight_heat: float = 0.6
    weight_aqi: float = 0.4

CFG = RuntimeConfig()

def get_config() -> Dict[str, Any]:
    return asdict(CFG)

def update_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    if "weather_provider_prefer" in patch:
        val = str(patch["weather_provider_prefer"]).lower().strip()
        if val not in ("auto", "openmeteo", "openweather"):
            raise ValueError("weather_provider_prefer must be one of: auto|openmeteo|openweather")
        CFG.weather_provider_prefer = val
    if "weight_heat" in patch:
        wh = float(patch["weight_heat"])
        if not (0.0 <= wh <= 1.0):
            raise ValueError("weight_heat must be 0.0..1.0")
        CFG.weight_heat = wh
    if "weight_aqi" in patch:
        wa = float(patch["weight_aqi"])
        if not (0.0 <= wa <= 1.0):
            raise ValueError("weight_aqi must be 0.0..1.0")
        CFG.weight_aqi = wa
    # keep weights unconstrained from summing to 1 on purpose; combine_tiers handles normalization if needed
    return get_config()

