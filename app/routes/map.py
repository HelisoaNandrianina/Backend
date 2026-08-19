# app/routes/map.py
from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.config import settings
from app.core.security import get_current_user

router = APIRouter(prefix="/api/map", tags=["Map"])


class MapCenterSchema(BaseModel):
    lat: float
    lng: float


class MapConfigResponse(BaseModel):
    center: MapCenterSchema
    zoom: float
    tile_style_url: str


@router.get("/config", response_model=MapConfigResponse)
def get_map_config(_user=Depends(get_current_user)):
    return MapConfigResponse(
        center=MapCenterSchema(lat=settings.MAP_DEFAULT_LAT, lng=settings.MAP_DEFAULT_LNG),
        zoom=settings.MAP_DEFAULT_ZOOM,
        tile_style_url=settings.MAP_TILE_STYLE_URL,
    )
