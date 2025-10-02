from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import live_risk  # ✅ use live_risk instead of risk

app = FastAPI(title="Wave Warn V2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
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

# ✅ mount only live_risk router
app.include_router(live_risk.router, tags=["risk"])

