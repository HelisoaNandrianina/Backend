# app/schemas/zone.py
import uuid
from typing import Literal

from pydantic import BaseModel


class ZoneCreateSchema(BaseModel):
    name: str
    boundary: dict | None = None


class ZoneUpdateSchema(BaseModel):
    name: str | None = None
    boundary: dict | None = None


class ZoneResponse(BaseModel):
    id: uuid.UUID
    name: str
    score: Literal["high", "medium", "low"]
    score_value: int
    coverage: float
    point_count: int
    revenue: float
    trend: float
    boundary: dict | None = None

    class Config:
        from_attributes = True
