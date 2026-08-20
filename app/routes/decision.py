# app/routes/decision.py
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import SessionLocal, get_db
from app.models.analysis_job import AnalysisJob
from app.models.recommendation import Recommendation
from app.schemas.decision import (
    GenerateAnalysisResponse,
    RecommendationResponse,
    ZoneRankingItem,
)
from app.services.decision import compute_zone_ranking, run_generate_analysis

router = APIRouter(prefix="/api/decision", tags=["Decision"])


def _run_in_background(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if job:
            run_generate_analysis(db, job)
    finally:
        db.close()


@router.get("/ranking", response_model=list[ZoneRankingItem])
def get_ranking(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return compute_zone_ranking(db)


@router.get("/recommendations", response_model=list[RecommendationResponse])
def get_recommendations(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Recommendation).order_by(Recommendation.potential.desc()).all()


@router.post("/generate-analysis", response_model=GenerateAnalysisResponse, status_code=202)
def generate_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    job = AnalysisJob(status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_in_background, job.id)
    return GenerateAnalysisResponse(job_id=job.id, status=job.status)