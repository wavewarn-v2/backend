from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import risk  # clean import

app = FastAPI(title="Wave Warn V2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
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

# mount router module
app.include_router(risk.router, tags=["risk"])
