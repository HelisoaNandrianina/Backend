# app/routes/dashboard.py
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.datapoint import DataPoint
from app.models.sync import SyncJob
from app.models.zone import Zone
from app.schemas.dashboard import (
    ActivityItemSchema,
    DashboardKpisResponse,
    RevenuePointSchema,
    SegmentationItemSchema,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _shift_month(dt: datetime, delta: int) -> datetime:
    month_index = dt.month - 1 + delta
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return dt.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/kpis", response_model=DashboardKpisResponse)
def get_kpis(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    active_points = db.query(func.count(DataPoint.id)).filter(DataPoint.status == "active").scalar()
    zones_count = db.query(func.count(Zone.id)).scalar()
    avg_score = db.query(func.coalesce(func.avg(DataPoint.score), 0)).scalar()

    return DashboardKpisResponse(
        active_points=active_points,
        zones_count=zones_count,
        avg_score=round(float(avg_score)),
        # En dur pour l'instant : dépend du futur module Notifications, qui n'existe
        # pas encore — pas de valeur arbitraire en attendant.
        active_alerts=0,
    )


@router.get("/revenue-evolution", response_model=list[RevenuePointSchema])
def get_revenue_evolution(
    months: int = Query(7, ge=1, le=36),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    current_month_start = _shift_month(datetime.utcnow(), 0)
    months_range = [_shift_month(current_month_start, -i) for i in range(months - 1, -1, -1)]

    rows = (
        db.query(
            func.date_trunc("month", DataPoint.created_at).label("month"),
            func.coalesce(func.sum(DataPoint.revenue), 0).label("revenue"),
        )
        .filter(DataPoint.created_at >= months_range[0])
        .group_by("month")
        .all()
    )
    revenue_by_month = {_month_key(row.month): float(row.revenue) for row in rows}

    return [
        RevenuePointSchema(month=_month_key(m), revenue=revenue_by_month.get(_month_key(m), 0.0))
        for m in months_range
    ]


@router.get("/segmentation", response_model=list[SegmentationItemSchema])
def get_segmentation(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = db.query(DataPoint.type, func.count(DataPoint.id)).group_by(DataPoint.type).all()
    return [SegmentationItemSchema(type=type_, count=count) for type_, count in rows]


@router.get("/activity", response_model=list[ActivityItemSchema])
def get_activity(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    sync_jobs = db.query(SyncJob).order_by(SyncJob.started_at.desc()).limit(limit).all()
    points = db.query(DataPoint).order_by(DataPoint.created_at.desc()).limit(limit).all()

    items = [
        ActivityItemSchema(
            type="sync",
            message=f"Synchronisation {job.status} — {job.records_imported} trajets importés",
            timestamp=job.started_at,
        )
        for job in sync_jobs
    ] + [
        ActivityItemSchema(
            type="point_created",
            message=f"Nouveau point ajouté : {point.name}",
            timestamp=point.created_at,
        )
        for point in points
    ]

    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items[:limit]
