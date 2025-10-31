# src/wavewarn/main.py
from pathlib import Path
import os

# ---- Load environment variables from backend/.env BEFORE importing routes ----
try:
    from dotenv import load_dotenv
    # This resolves to .../WaveWarn/backend/.env regardless of CWD
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
except Exception as e:
    # Don't crash if dotenv isn't installed; you can still export vars in shell
    print("[ENV] dotenv load skipped/failed:", e)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---- Import routers AFTER env is loaded ----
from .routes import power
from .routes import timeline
from .routes import live_risk
from .routes import risk
from .routes import openmeteo_hourly
from .routes import forecast_unified
from .routes import air_quality_openmeteo
from .routes import forecast_air_summary
from .routes import forecast_air_hourly
from .routes import risk_heat
from .routes import weather_openmeteo
from .routes import risk_unified
from .routes import risk_unified_daily
from .routes import waqi
from .routes import weather_provider 
from .routes import weather_openweather
from .routes import openaq
from .routes import admin_status
from .routes import admin_config
from .routes import heatwave_analysis
from .middleware.logging import RequestLogMiddleware
# from .routes import imd  # keep commented until you add routes/imd.py

app = FastAPI(title="Wave Warn V2 API")

# ---- CORS (as you had) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)

# ---- Core health & utility routes ----
@app.get("/")
def root():
    return {"msg": "Wave Warn V2 backend is running", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "wavewarn-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

# (Optional) quick env debug endpoint – safe (masked)
@app.get("/__env")
def __env():
    k = os.getenv("OPENAQ_API_KEY") or ""
    masked = (k[:4] + "***" + k[-4:]) if len(k) >= 8 else ("set" if k else "missing")
    return {"OPENAQ_API_KEY_loaded": bool(k), "key_preview": masked}

# (Optional) print all registered routes & env status on startup
@app.on_event("startup")
async def _startup_debug():
    k = os.getenv("OPENAQ_API_KEY")
    masked = (k[:4] + "***" + k[-4:]) if k and len(k) >= 8 else (k or "")
    print(f"\n[ENV DEBUG] OPENAQ_API_KEY loaded? {'YES' if k else 'NO'} {masked}\n")
    print("=== Registered routes ===")
    for r in app.routes:
        try:
            methods = ",".join(sorted(r.methods)) if hasattr(r, "methods") else "-"
            print(f"{methods:15} {getattr(r, 'path', '-')}")
        except Exception:
            pass
    print("=========================\n")

# ---- Register feature routers ----
app.include_router(power.router)
app.include_router(timeline.router, tags=["risk"])
app.include_router(live_risk.router, tags=["risk"])
app.include_router(risk.router, tags=["risk"])
app.include_router(openmeteo_hourly.router, tags=["sources"])
app.include_router(forecast_unified.router, tags=["forecast"])
app.include_router(openaq.router, tags=["sources-openaq"])
app.include_router(air_quality_openmeteo.router, tags=["sources-air"])
app.include_router(forecast_air_summary.router, tags=["forecast"])
app.include_router(forecast_air_hourly.router, tags=["forecast"])
app.include_router(weather_openmeteo.router, tags=["sources-weather"])
app.include_router(risk_heat.router, tags=["risk"])
app.include_router(risk_unified.router, tags=["risk"])
app.include_router(risk_unified_daily.router, tags=["risk"])
app.include_router(waqi.router, tags=["sources-air"])
app.include_router(weather_provider.router, tags=["sources-weather"])
app.include_router(weather_openweather.router, tags=["sources-weather"])
app.include_router(admin_status.router)
app.include_router(admin_config.router)
app.include_router(heatwave_analysis.router, tags=["risk"])
# app.include_router(imd.router, tags=["sources-imd"])  # keep commented for now

