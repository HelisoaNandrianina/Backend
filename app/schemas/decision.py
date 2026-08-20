# app/schemas/decision.py
import uuid
from datetime import datetime

from pydantic import BaseModel


class ZoneRankingItem(BaseModel):
    zone: str
    score: float
    revenue: float
    points_count: int
    trend: str


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    zone: str
    title: str
    message: str
    urgency: str
    potential: int
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateAnalysisResponse(BaseModel):
    job_id: uuid.UUID
    status: str