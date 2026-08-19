# app/routes/analysis.py
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.datapoint import DataPoint
from app.schemas.analysis import (
    DensityPointSchema,
    DistanceRequestSchema,
    DistanceResponseSchema,
    PointRefSchema,
)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def _resolve_point(db: Session, ref: PointRefSchema) -> tuple[float, float]:
    if ref.point_id is not None:
        try:
            point_uuid = uuid.UUID(ref.point_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="point_id invalide")

        point = db.query(DataPoint).filter(DataPoint.id == point_uuid).first()
        if not point:
            raise HTTPException(status_code=404, detail="Point introuvable")
        return point.lat, point.lng

    return ref.lat, ref.lng


@router.post("/distance", response_model=DistanceResponseSchema)
def compute_distance(
    body: DistanceRequestSchema,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    origin_lat, origin_lng = _resolve_point(db, body.origin)
    dest_lat, dest_lng = _resolve_point(db, body.destination)

    distance_km = _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    duration_min = distance_km / body.avg_speed_kmh * 60

    return DistanceResponseSchema(
        distance_km=round(distance_km, 3),
        duration_min=round(duration_min, 1),
        # Distance à vol d'oiseau (grand cercle), PAS un itinéraire routier réel : aucun
        # moteur de routing (OSRM/GraphHopper) n'est intégré. Reste toujours true tant
        # que c'est le cas — ne pas interpréter duration_min comme un temps de trajet réel.
        is_straight_line=True,
    )


@router.get("/density", response_model=list[DensityPointSchema])
def get_density(
    zone: str | None = None,
    type: str | None = None,
    status: str | None = None,
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    # Projection volontairement allégée (3 nombres/ligne) pour alimenter directement un
    # layer heatmap MapLibre — pas un DataPointResponse complet ni une liste paginée
    # comme GET /api/points. Pour un export complet, GET /api/points/export existe déjà.
    query = db.query(DataPoint.lat, DataPoint.lng, DataPoint.score)
    if zone:
        query = query.filter(DataPoint.zone == zone)
    if type:
        query = query.filter(DataPoint.type == type)
    if status:
        query = query.filter(DataPoint.status == status)

    rows = query.limit(limit).all()
    return [DensityPointSchema(lat=lat, lng=lng, weight=score) for lat, lng, score in rows]
