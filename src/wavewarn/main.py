# src/wavewarn/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import live_risk, timeline  # import both routers

app = FastAPI(title="Wave Warn V2 API")

# CORS for dev; tighten later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"msg": "Wave Warn V2 backend is running", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "wavewarn-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

# Mount routers
app.include_router(live_risk.router, tags=["risk"])
app.include_router(timeline.router, tags=["timeline"])

