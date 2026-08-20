# app/routes/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings as env_settings
from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.settings import Settings
from app.models.user import User
from app.schemas.settings import (
    AlertSettings,
    DataSettings,
    SecuritySettings,
    SettingsResponse,
    SettingsUpdateRequest,
    SystemSettings,
)

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _get_or_create(db: Session) -> Settings:
    row = db.query(Settings).filter(Settings.id == 1).first()
    if not row:
        row = Settings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _to_response(row: Settings) -> SettingsResponse:
    return SettingsResponse(
        system=SystemSettings(
            sync_interval_minutes=env_settings.SYNC_INTERVAL_MINUTES,
            map_default_lat=env_settings.MAP_DEFAULT_LAT,
            map_default_lng=env_settings.MAP_DEFAULT_LNG,
            map_default_zoom=env_settings.MAP_DEFAULT_ZOOM,
        ),
        alerts=AlertSettings(
            score_threshold=row.alert_score_threshold,
            revenue_drop_percent=row.alert_revenue_drop_percent,
        ),
        security=SecuritySettings(
            session_timeout_minutes=row.security_session_timeout_minutes,
            require_strong_password=row.security_require_strong_password,
        ),
        data=DataSettings(
            auto_sync_enabled=row.data_auto_sync_enabled,
            retention_days=row.data_retention_days,
        ),
        updated_at=row.updated_at,
    )


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    row = _get_or_create(db)
    return _to_response(row)


@router.put("", response_model=SettingsResponse)
def update_settings(
    body: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    row = _get_or_create(db)

    if body.alerts is not None:
        row.alert_score_threshold = body.alerts.score_threshold
        row.alert_revenue_drop_percent = body.alerts.revenue_drop_percent
    if body.security is not None:
        row.security_session_timeout_minutes = body.security.session_timeout_minutes
        row.security_require_strong_password = body.security.require_strong_password
    if body.data is not None:
        row.data_auto_sync_enabled = body.data.auto_sync_enabled
        row.data_retention_days = body.data.retention_days

    row.updated_by = user.id
    db.commit()
    db.refresh(row)
    return _to_response(row)