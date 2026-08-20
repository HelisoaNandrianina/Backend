# app/routes/notifications.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import MessageResponse, NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    type: str | None = None,
    priority: str | None = None,
    read: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Notification)
    if type:
        query = query.filter(Notification.type == type)
    if priority:
        query = query.filter(Notification.priority == priority)
    if read is not None:
        query = query.filter(Notification.read == read)

    return query.order_by(Notification.timestamp.desc()).limit(limit).all()


def _parse_uuid(notification_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant invalide")


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    notif = db.query(Notification).filter(Notification.id == _parse_uuid(notification_id)).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    notif.read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/mark-all-read", response_model=MessageResponse)
def mark_all_read(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.read == False).update({"read": True})
    db.commit()
    return {"message": "Toutes les notifications ont été marquées comme lues"}


@router.delete("/{notification_id}", response_model=MessageResponse)
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    notif = db.query(Notification).filter(Notification.id == _parse_uuid(notification_id)).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    db.delete(notif)
    db.commit()
    return {"message": "Notification supprimée"}