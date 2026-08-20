# app/models/recommendation.py
import uuid

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Recommendation(Base):
    """Recommandations régénérées à chaque POST /api/decision/generate-analysis
    (l'ancienne génération est remplacée, pas cumulée)."""
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    urgency = Column(String, nullable=False, default="normal")
    potential = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)