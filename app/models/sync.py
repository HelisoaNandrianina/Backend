# app/models/sync.py
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class MobilityTrip(Base):
    __tablename__ = "mobility_trips"
    # UNIQUE(device_id, start_time) rend l'upsert idempotent : une resynchro du
    # même trajet source met à jour la ligne existante au lieu de la dupliquer.
    __table_args__ = (
        UniqueConstraint("device_id", "start_time", name="uq_mobility_trips_device_start"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_min = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    avg_speed_kmh = Column(Float, nullable=True)
    max_speed_kmh = Column(Float, nullable=True)
    speed_p50 = Column(Float, nullable=True)
    speed_p90 = Column(Float, nullable=True)
    origin_suburb = Column(String, nullable=True)
    origin_city = Column(String, nullable=True, index=True)
    origin_region = Column(String, nullable=True)
    origin_lat = Column(Float, nullable=True)
    origin_lon = Column(Float, nullable=True)
    destination_suburb = Column(String, nullable=True)
    destination_city = Column(String, nullable=True, index=True)
    destination_region = Column(String, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lon = Column(Float, nullable=True)
    places_along_route = Column(JSONB, nullable=False, default=list)
    hour_of_start = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    season = Column(String, nullable=True)
    is_weekend = Column(Boolean, nullable=True)
    gap_count = Column(Integer, nullable=True)
    point_count = Column(Integer, nullable=True)
    status = Column(String, nullable=True, index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)  # "manual" | "scheduled"
    status = Column(String, nullable=False, default="running")  # "running" | "success" | "failed"
    records_imported = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
