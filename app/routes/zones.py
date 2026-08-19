# app/routes/zones.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.datapoint import DataPoint
from app.models.zone import Zone
from app.schemas.user import MessageResponse
from app.schemas.zone import ZoneCreateSchema, ZoneResponse, ZoneUpdateSchema

router = APIRouter(prefix="/api/zones", tags=["Zones"])


def _compute_zone_metrics(db: Session, zone_name: str) -> dict:
    row = (
        db.query(
            func.count(DataPoint.id).label("point_count"),
            func.coalesce(func.sum(DataPoint.revenue), 0).label("revenue"),
            func.coalesce(func.avg(DataPoint.score), 0).label("avg_score"),
            func.coalesce(
                func.sum(case((DataPoint.status == "active", 1), else_=0)), 0
            ).label("active_count"),
        )
        .filter(DataPoint.zone == zone_name)
        .one()
    )

    point_count = int(row.point_count)
    revenue = float(row.revenue)
    score_value = round(float(row.avg_score))
    active_count = int(row.active_count)

    # Proxy en l'absence d'une vraie analyse de couverture géographique par polygone :
    # taux de points actifs dans la zone. Le futur module Analyse Géospatiale calculera
    # une vraie couverture surfacique.
    coverage = round(active_count / point_count * 100, 2) if point_count > 0 else 0.0
    score = "high" if score_value >= 80 else "medium" if score_value >= 60 else "low"

    return {
        "score": score,
        "score_value": score_value,
        "coverage": coverage,
        "point_count": point_count,
        "revenue": revenue,
        # Nécessiterait un historique d'instantanés qui n'existe pas encore — pas de
        # valeur arbitraire ou aléatoire en attendant.
        "trend": 0.0,
    }


def _to_response(zone: Zone, metrics: dict) -> ZoneResponse:
    return ZoneResponse(id=zone.id, name=zone.name, boundary=zone.boundary, **metrics)


@router.get("", response_model=list[ZoneResponse])
def list_zones(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    zones = db.query(Zone).order_by(Zone.name).all()
    return [_to_response(zone, _compute_zone_metrics(db, zone.name)) for zone in zones]


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    return _to_response(zone, _compute_zone_metrics(db, zone.name))


@router.post("", response_model=ZoneResponse, status_code=201)
def create_zone(body: ZoneCreateSchema, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if db.query(Zone).filter(Zone.name == body.name).first():
        raise HTTPException(status_code=400, detail="Nom de zone déjà utilisé")

    zone = Zone(name=body.name, boundary=body.boundary)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return _to_response(zone, _compute_zone_metrics(db, zone.name))


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: uuid.UUID,
    body: ZoneUpdateSchema,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Si `name` change, les DataPoint existants dont zone == ancien nom ne sont PAS
    renommés automatiquement (zone est un champ texte libre, aucune FK ne les lie) :
    leurs métriques resteront rattachées à l'ancien nom jusqu'à correction manuelle."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    updates = body.model_dump(exclude_unset=True)

    new_name = updates.get("name")
    if new_name is not None and new_name != zone.name:
        if db.query(Zone).filter(Zone.name == new_name, Zone.id != zone_id).first():
            raise HTTPException(status_code=400, detail="Nom de zone déjà utilisé")

    for field, value in updates.items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return _to_response(zone, _compute_zone_metrics(db, zone.name))


@router.delete("/{zone_id}", response_model=MessageResponse)
def delete_zone(zone_id: uuid.UUID, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    has_points = db.query(DataPoint.id).filter(DataPoint.zone == zone.name).first() is not None
    if has_points:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer une zone contenant des points — réaffectez ou supprimez d'abord ses points",
        )

    db.delete(zone)
    db.commit()
    return {"message": "Zone supprimée avec succès"}
