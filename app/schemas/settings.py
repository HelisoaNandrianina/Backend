# app/schemas/settings.py
from datetime import datetime

from pydantic import BaseModel


class SystemSettings(BaseModel):
    sync_interval_minutes: int
    map_default_lat: float
    map_default_lng: float
    map_default_zoom: float


class AlertSettings(BaseModel):
    score_threshold: int
    revenue_drop_percent: int


class SecuritySettings(BaseModel):
    session_timeout_minutes: int
    require_strong_password: bool


class DataSettings(BaseModel):
    auto_sync_enabled: bool
    retention_days: int


class SettingsResponse(BaseModel):
    system: SystemSettings
    alerts: AlertSettings
    security: SecuritySettings
    data: DataSettings
    updated_at: datetime | None = None


class SettingsUpdateRequest(BaseModel):
    alerts: AlertSettings | None = None
    security: SecuritySettings | None = None
    data: DataSettings | None = None