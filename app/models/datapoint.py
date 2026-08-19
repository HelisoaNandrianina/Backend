# app/models/datapoint.py
import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.database import Base


class DataPoint(Base):
    __tablename__ = "data_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    # Champ texte libre plutôt qu'une FK : il n'existe pas encore de table Zones
    # référentielle dans le projet, et le référentiel des zones (Madagascar) n'est
    # pas stable/figé pour l'instant. À revoir si un module Zones est introduit.
    zone = Column(String, nullable=False, index=True)
    score = Column(Integer, nullable=False, default=50)
    status = Column(String, nullable=False, default="pending", index=True)  # active | inactive | pending
    type = Column(String, nullable=False, index=True)  # client | prospect | partner
    revenue = Column(Float, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
