# src/wavewarn/routes/admin_status.py
from fastapi import APIRouter
import os
from ..utils.cache import wx_cache

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/status")
def status():
    return {
        "ok": True,
        "env": {
            "WEATHER_PROVIDER_PREFER": os.getenv("WEATHER_PROVIDER_PREFER", "auto"),
            "OWM_MAX_PER_MINUTE": os.getenv("OWM_MAX_PER_MINUTE", "50"),
            "OWM_API_KEY_set": bool(os.getenv("OWM_API_KEY")),
        },
        "cache": {
            "weather": wx_cache.stats(),
        }
    }

