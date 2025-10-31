# src/wavewarn/routes/admin_config.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..utils.settings import get_config, update_config

router = APIRouter(prefix="/admin", tags=["admin"])

class ConfigPatch(BaseModel):
    weather_provider_prefer: Optional[str] = Field(None, description="auto|openmeteo|openweather")
    weight_heat: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_aqi: Optional[float]  = Field(None, ge=0.0, le=1.0)

@router.get("/config")
def read_config():
    return {"ok": True, "config": get_config()}

@router.post("/config")
def write_config(patch: ConfigPatch):
    try:
        new_cfg = update_config({k: v for k, v in patch.dict().items() if v is not None})
        return {"ok": True, "config": new_cfg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

