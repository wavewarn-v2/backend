# src/wavewarn/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.risk import router as risk_router

app = FastAPI(title="Wave Warn V2 API")

# CORS: allow local dev (emulator, phone, web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
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

# NEW: simple ping
@app.get("/ping")
def ping():
    return {"status": "ok"}

# Mount risk routes
app.include_router(risk_router, prefix="", tags=["risk"])
# src/wavewarn/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.risk import router as risk_router

app = FastAPI(title="Wave Warn V2 API")

# CORS: allow local dev (emulator, phone, web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
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

# NEW: simple ping
@app.get("/ping")
def ping():
    return {"status": "ok"}

# Mount risk routes
app.include_router(risk_router, prefix="", tags=["risk"])
