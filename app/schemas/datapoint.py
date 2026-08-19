# app/schemas/datapoint.py
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

VALID_TYPES = ["client", "prospect", "partner"]
VALID_STATUSES = ["active", "inactive", "pending"]


class DataPointCreateSchema(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    zone: str
    type: str
    status: str = "pending"
    score: int = Field(default=50, ge=0, le=100)
    revenue: float = 0

    def model_post_init(self, __context) -> None:
        if self.type not in VALID_TYPES:
            raise ValueError(f"Type invalide, attendu parmi {VALID_TYPES}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Statut invalide, attendu parmi {VALID_STATUSES}")


class DataPointUpdateSchema(BaseModel):
    name: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    zone: str | None = None
    type: str | None = None
    status: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    revenue: float | None = None

    def model_post_init(self, __context) -> None:
        if self.type is not None and self.type not in VALID_TYPES:
            raise ValueError(f"Type invalide, attendu parmi {VALID_TYPES}")
        if self.status is not None and self.status not in VALID_STATUSES:
            raise ValueError(f"Statut invalide, attendu parmi {VALID_STATUSES}")


class DataPointResponse(BaseModel):
    id: uuid.UUID
    name: str
    lat: float
    lng: float
    zone: str
    score: int
    status: str
    type: str
    revenue: float
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataPointListResponse(BaseModel):
    items: list[DataPointResponse]
    total: int
    page: int
    page_size: int


class ImportErrorDetail(BaseModel):
    line: int
    reason: str


class ImportReportSchema(BaseModel):
    inserted: int
    rejected: int
    errors: list[ImportErrorDetail]
