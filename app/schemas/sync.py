# app/schemas/sync.py
import uuid
from datetime import datetime

from pydantic import BaseModel


class TriggerSyncResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    source_url: str
    trigger_type: str
    status: str
    records_imported: int
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class MobilityTripResponse(BaseModel):
    id: uuid.UUID
    device_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_min: float | None = None
    distance_km: float | None = None
    avg_speed_kmh: float | None = None
    max_speed_kmh: float | None = None
    speed_p50: float | None = None
    speed_p90: float | None = None
    origin_suburb: str | None = None
    origin_city: str | None = None
    origin_region: str | None = None
    origin_lat: float | None = None
    origin_lon: float | None = None
    destination_suburb: str | None = None
    destination_city: str | None = None
    destination_region: str | None = None
    destination_lat: float | None = None
    destination_lon: float | None = None
    places_along_route: list = []
    hour_of_start: int | None = None
    day_of_week: int | None = None
    month: int | None = None
    season: str | None = None
    is_weekend: bool | None = None
    gap_count: int | None = None
    point_count: int | None = None
    status: str | None = None
    synced_at: datetime

    model_config = {"from_attributes": True}


class MobilityTripListResponse(BaseModel):
    items: list[MobilityTripResponse]
    total: int
    page: int
    page_size: int
