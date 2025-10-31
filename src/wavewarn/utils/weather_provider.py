# src/wavewarn/utils/weather_provider.py
from typing import Dict, Any
from .openmeteo_weather_client import fetch_weather_hourly as om_fetch, OMWeatherError
from .openweather_client      import fetch_hourly         as owm_fetch, OWMError

class WeatherProviderError(Exception):
    pass

def get_weather_hourly(lat: float, lon: float, *, provider: str = "openmeteo",
                       days: int = 5, hours: int | None = None) -> Dict[str, Any]:
    try:
        if provider == "openmeteo":
            return {"provider": "openmeteo", **om_fetch(lat, lon, days=days)}
        elif provider == "openweather":
            return {"provider": "openweather", **owm_fetch(lat, lon, days=days, hours=hours)}
        elif provider == "auto":
            try:
                return {"provider": "openmeteo", **om_fetch(lat, lon, days=days)}
            except Exception:
                return {"provider": "openweather", **owm_fetch(lat, lon, days=days, hours=hours)}
        else:
            raise WeatherProviderError(f"Unknown provider: {provider}")
    except (OMWeatherError, OWMError) as e:
        raise WeatherProviderError(str(e)) from e

# Back-compat alias (prevents old imports from crashing)
get_hourly_weather = get_weather_hourly

