# app/models/notification.py
import uuid

from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, default="normal", index=True)
    read = Column(Boolean, nullable=False, default=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)