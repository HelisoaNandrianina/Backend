# app/routes/dashboard.py
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.datapoint import DataPoint
from app.models.sync import SyncJob
from app.models.zone import Zone
from app.schemas.dashboard import (
    ActivityItemSchema,
    AdvancedZoneStatSchema,
    DashboardKpisResponse,
    RevenuePointSchema,
    ScoreRevenuePointSchema,
    SegmentationItemSchema,
    TopPerformanceItemSchema,
)
from app.services.decision import compute_zone_ranking

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

_PERIOD_MAP = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "180d": timedelta(days=180),
    "365d": timedelta(days=365),
}


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _shift_month(dt: datetime, delta: int) -> datetime:
    month_index = dt.month - 1 + delta
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return dt.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def _parse_period(period: str) -> timedelta:
    if period not in _PERIOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"period invalide, valeurs acceptées : {', '.join(_PERIOD_MAP)}",
        )
    return _PERIOD_MAP[period]


@router.get("/kpis", response_model=DashboardKpisResponse)
def get_kpis(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    active_points = db.query(func.count(DataPoint.id)).filter(DataPoint.status == "active").scalar()
    zones_count = db.query(func.count(Zone.id)).scalar()
    avg_score = db.query(func.coalesce(func.avg(DataPoint.score), 0)).scalar()

    return DashboardKpisResponse(
        active_points=active_points,
        zones_count=zones_count,
        avg_score=round(float(avg_score)),
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


@router.get("/advanced", response_model=list[AdvancedZoneStatSchema])
def get_advanced(
    period: str = Query("30d"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    window = _parse_period(period)
    cutoff = datetime.utcnow() - window

    rows = (
        db.query(
            DataPoint.zone,
            func.coalesce(func.avg(DataPoint.score), 0).label("score"),
            func.coalesce(func.sum(DataPoint.revenue), 0).label("revenue"),
            func.count(DataPoint.id).label("points_count"),
        )
        .filter(DataPoint.created_at >= cutoff)
        .group_by(DataPoint.zone)
        .all()
    )

    return [
        AdvancedZoneStatSchema(
            zone=zone,
            score=round(float(score), 1),
            revenue=round(float(revenue), 2),
            points_count=points_count,
        )
        for zone, score, revenue, points_count in rows
    ]


@router.get("/score-vs-revenue", response_model=list[ScoreRevenuePointSchema])
def get_score_vs_revenue(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    ranking = compute_zone_ranking(db)
    return [
        ScoreRevenuePointSchema(zone=row["zone"], score=row["score"], revenue=row["revenue"])
        for row in ranking
    ]


@router.get("/top-performances", response_model=list[TopPerformanceItemSchema])
def get_top_performances(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    ranking = compute_zone_ranking(db)[:limit]
    return [
        TopPerformanceItemSchema(rank=i + 1, zone=row["zone"], score=row["score"], revenue=row["revenue"])
        for i, row in enumerate(ranking)
    ]