# app/services/notifications.py
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    title: str,
    message: str,
    type: str,
    priority: str = "normal",
) -> Notification:
    notif = Notification(title=title, message=message, type=type, priority=priority)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif