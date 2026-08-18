# app/services/sync.py
import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.sync import MobilityTrip, SyncJob

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
MAX_ATTEMPTS = 3  # tentative initiale + 2 retries
BACKOFF_BASE_SECONDS = 2

_UPSERT_EXCLUDED_COLUMNS = {"id", "device_id", "start_time"}
_UPDATE_COLUMNS = [c.name for c in MobilityTrip.__table__.columns if c.name not in _UPSERT_EXCLUDED_COLUMNS]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _row_from_line(line: str) -> dict:
    data = json.loads(line)
    return {
        "device_id": data.get("device_id"),
        "start_time": _parse_datetime(data.get("start_time")),
        "end_time": _parse_datetime(data.get("end_time")),
        "duration_min": data.get("duration_min"),
        "distance_km": data.get("distance_km"),
        "avg_speed_kmh": data.get("avg_speed_kmh"),
        "max_speed_kmh": data.get("max_speed_kmh"),
        "speed_p50": data.get("speed_p50"),
        "speed_p90": data.get("speed_p90"),
        "origin_suburb": data.get("origin_suburb"),
        "origin_city": data.get("origin_city"),
        "origin_region": data.get("origin_region"),
        "origin_lat": data.get("origin_lat"),
        "origin_lon": data.get("origin_lon"),
        "destination_suburb": data.get("destination_suburb"),
        "destination_city": data.get("destination_city"),
        "destination_region": data.get("destination_region"),
        "destination_lat": data.get("destination_lat"),
        "destination_lon": data.get("destination_lon"),
        "places_along_route": data.get("places_along_route") or [],
        "hour_of_start": data.get("hour_of_start"),
        "day_of_week": data.get("day_of_week"),
        "month": data.get("month"),
        "season": data.get("season"),
        "is_weekend": data.get("is_weekend"),
        "gap_count": data.get("gap_count"),
        "point_count": data.get("point_count"),
        "status": data.get("status"),
    }


def _upsert_batch(db: Session, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = pg_insert(MobilityTrip).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["device_id", "start_time"],
        set_={col: getattr(stmt.excluded, col) for col in _UPDATE_COLUMNS},
    )
    db.execute(stmt)
    db.commit()


async def _fetch_and_upsert(db: Session, source_url: str) -> int:
    imported = 0
    batch: list[dict] = []
    # Streaming ligne par ligne : le flux JSONL peut contenir un très grand nombre
    # de trajets, on évite donc de charger toute la réponse en mémoire.
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", source_url) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                batch.append(_row_from_line(line))
                if len(batch) >= BATCH_SIZE:
                    _upsert_batch(db, batch)
                    imported += len(batch)
                    batch = []
    _upsert_batch(db, batch)
    imported += len(batch)
    return imported


async def run_trip_sync(db: Session, source_url: str, trigger_type: str, job: SyncJob | None = None) -> SyncJob:
    if job is None:
        job = SyncJob(
            source_url=source_url,
            trigger_type=trigger_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    last_error: Exception | None = None
    imported = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            imported = await _fetch_and_upsert(db, source_url)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            db.rollback()
            logger.error("Sync job %s: attempt %s/%s failed: %s", job.id, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(BACKOFF_BASE_SECONDS ** attempt)

    job.finished_at = datetime.now(timezone.utc)
    if last_error is None:
        job.status = "success"
        job.records_imported = imported
        logger.info("Sync job %s completed: %s trip(s) imported", job.id, imported)
    else:
        job.status = "failed"
        job.records_imported = imported
        job.error_message = str(last_error)
        logger.error("Sync job %s failed after %s attempts: %s", job.id, MAX_ATTEMPTS, last_error)

    db.commit()
    db.refresh(job)
    return job
