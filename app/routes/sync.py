# app/routes/sync.py
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import get_current_user, require_admin
from app.database import SessionLocal, get_db
from app.models.sync import MobilityTrip, SyncJob
from app.schemas.sync import (
    MobilityTripListResponse,
    MobilityTripResponse,
    SyncJobResponse,
    TriggerSyncResponse,
)
from app.services.sync import run_trip_sync

router = APIRouter(tags=["Sync"])


async def _run_sync_in_background(job_id: uuid.UUID, source_url: str, trigger_type: str) -> None:
    # Une tâche de fond FastAPI s'exécute après la fermeture de la session de la
    # requête d'origine : on ouvre donc une session dédiée pour toute la durée du job.
    db = SessionLocal()
    try:
        job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        await run_trip_sync(db, source_url, trigger_type, job=job)
    finally:
        db.close()


@router.post("/api/sync/trigger", response_model=TriggerSyncResponse, status_code=202)
def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    job = SyncJob(source_url=settings.SYNC_SOURCE_URL, trigger_type="manual", status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_sync_in_background, job.id, settings.SYNC_SOURCE_URL, "manual")
    return TriggerSyncResponse(job_id=job.id, status=job.status)


@router.get("/api/sync/status", response_model=SyncJobResponse)
def sync_status(
    job_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(SyncJob)
    if job_id is not None:
        job = query.filter(SyncJob.id == job_id).first()
    else:
        job = query.order_by(SyncJob.started_at.desc()).first()

    if not job:
        raise HTTPException(status_code=404, detail="Aucune synchronisation trouvée")
    return job


@router.get("/api/mobility-trips", response_model=MobilityTripListResponse)
def list_mobility_trips(
    device_id: str | None = None,
    origin_city: str | None = None,
    destination_city: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(MobilityTrip)
    if device_id:
        query = query.filter(MobilityTrip.device_id == device_id)
    if origin_city:
        query = query.filter(MobilityTrip.origin_city == origin_city)
    if destination_city:
        query = query.filter(MobilityTrip.destination_city == destination_city)
    if status:
        query = query.filter(MobilityTrip.status == status)
    if start_date:
        query = query.filter(MobilityTrip.start_time >= start_date)
    if end_date:
        query = query.filter(MobilityTrip.start_time <= end_date)

    total = query.count()
    items = (
        query.order_by(MobilityTrip.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MobilityTripListResponse(items=items, total=total, page=page, page_size=page_size)
