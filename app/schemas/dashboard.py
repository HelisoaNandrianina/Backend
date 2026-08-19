# app/schemas/dashboard.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DashboardKpisResponse(BaseModel):
    active_points: int
    zones_count: int
    avg_score: int
    active_alerts: int


class RevenuePointSchema(BaseModel):
    month: str
    revenue: float


class SegmentationItemSchema(BaseModel):
    type: str
    count: int


class ActivityItemSchema(BaseModel):
    type: Literal["sync", "point_created"]
    message: str
    timestamp: datetime
