from fastapi import FastAPI
from .routers import live_risk

app = FastAPI(title="Wave Warn API", version="0.1")

# Mount routers
app.include_router(live_risk.router)

# Optional health check
@app.get("/health")
def health():
    return {"ok": True}
