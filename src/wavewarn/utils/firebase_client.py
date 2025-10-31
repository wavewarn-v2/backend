# src/wavewarn/utils/firebase_client.py
import os
from google.cloud import firestore

_db = None
def db():
    global _db
    if _db is None:
        _db = firestore.Client(project=os.getenv("FIREBASE_PROJECT_ID"))
    return _db

def save_hourly_snapshot(lat, lon, payload):
    doc = {
        "lat": lat, "lon": lon,
        "ts": payload.get("peak", {}).get("ts"),
        "peak": payload.get("peak"),
        "hours": payload.get("hours"),
        "weights": payload.get("weights"),
        "source": payload.get("source"),
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    return db().collection("risk_snapshots").add(doc)

