from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import live_risk

app = FastAPI(title="Wave Warn API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(live_risk.router)
