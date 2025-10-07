from pydantic import BaseModel
from typing import Dict, List

class RiskPoint(BaseModel):
    hour: int
    score: int
    tier: str
    drivers: Dict[str, float]

class RiskTimeline(BaseModel):
    ok: bool
    location: Dict[str, float]
    points: List[RiskPoint]

