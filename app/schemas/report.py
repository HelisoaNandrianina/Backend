# app/schemas/report.py
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    type: str
    zones: list[str] | str = "all"
    format: Literal["pdf", "xlsx"]


class ReportResponse(BaseModel):
    id: uuid.UUID
    type: str
    zones: list[str] | str
    format: str
    status: str
    created_at: datetime
    finished_at: datetime | None = None

    class Config:
        from_attributes = True


class GenerateReportResponse(BaseModel):
    report_id: uuid.UUID
    status: str