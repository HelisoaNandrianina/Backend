# app/schemas/notification.py
import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    type: str
    priority: str
    read: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str