# app/schemas/analysis.py
from pydantic import BaseModel, Field


class PointRefSchema(BaseModel):
    point_id: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    def model_post_init(self, __context) -> None:
        if self.point_id is None and (self.lat is None or self.lng is None):
            raise ValueError("Fournissez point_id, ou bien lat ET lng")


class DistanceRequestSchema(BaseModel):
    origin: PointRefSchema
    destination: PointRefSchema
    avg_speed_kmh: float = 40


class DistanceResponseSchema(BaseModel):
    distance_km: float
    duration_min: float
    is_straight_line: bool = True


class DensityPointSchema(BaseModel):
    lat: float
    lng: float
    weight: int
