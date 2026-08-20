# app/routes/reports.py
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import SessionLocal, get_db
from app.models.report import Report
from app.schemas.report import GenerateReportResponse, ReportGenerateRequest, ReportResponse
from app.services.reports import run_generate_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _run_in_background(report_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            run_generate_report(db, report)
    finally:
        db.close()


@router.get("", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Report).order_by(Report.created_at.desc()).all()


@router.post("/generate", response_model=GenerateReportResponse, status_code=202)
def generate_report(
    body: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    report = Report(
        type=body.type,
        zones=body.zones,
        format=body.format,
        status="generating",
        created_by=user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(_run_in_background, report.id)
    return GenerateReportResponse(report_id=report.id, status=report.status)


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if report.status != "ready" or not report.file_path:
        raise HTTPException(status_code=409, detail="Le rapport n'est pas encore prêt")
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur")

    media_type = (
        "application/pdf"
        if report.format == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"rapport_{report.type}.{report.format}"
    return FileResponse(report.file_path, media_type=media_type, filename=filename)


@router.delete("/{report_id}")
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")

    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)

    db.delete(report)
    db.commit()
    return {"message": "Rapport supprimé"}