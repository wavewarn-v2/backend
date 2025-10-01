from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Wave Warn V2 backend is running"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "wavewarn-backend"}
