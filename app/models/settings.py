# app/models/settings.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, func

from app.database import Base


class Settings(Base):
    """Ligne unique (id=1) : réglages modifiables via l'API. Les réglages
    'système' (intervalle de synchro, carte par défaut) restent dans .env
    car ils nécessitent un redémarrage — non stockés ici."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    alert_score_threshold = Column(Integer, nullable=False, default=40)
    alert_revenue_drop_percent = Column(Integer, nullable=False, default=20)
    security_session_timeout_minutes = Column(Integer, nullable=False, default=120)
    security_require_strong_password = Column(Boolean, nullable=False, default=True)
    data_auto_sync_enabled = Column(Boolean, nullable=False, default=True)
    data_retention_days = Column(Integer, nullable=False, default=365)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)