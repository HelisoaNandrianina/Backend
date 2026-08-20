# app/services/reports.py
import os
from datetime import datetime, timezone

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.report import Report
from app.services.decision import compute_zone_ranking
from app.services.notifications import create_notification

REPORTS_DIR = "static/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

_TABLE_HEADER_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
])


def _filter_ranking(ranking: list[dict], zones) -> list[dict]:
    if zones in (None, "all"):
        return ranking
    zone_set = set(zones)
    return [row for row in ranking if row["zone"] in zone_set]


def _write_xlsx(path: str, report_type: str, ranking: list[dict], recommendations: list[Recommendation]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Classement"
    ws.append(["Zone", "Score", "Revenu", "Points", "Tendance"])
    for row in ranking:
        ws.append([row["zone"], row["score"], row["revenue"], row["points_count"], row["trend"]])

    if report_type == "Stratégique" and recommendations:
        ws2 = wb.create_sheet("Recommandations")
        ws2.append(["Zone", "Titre", "Message", "Urgence", "Potentiel"])
        for rec in recommendations:
            ws2.append([rec.zone, rec.title, rec.message, rec.urgency, rec.potential])

    wb.save(path)


def _write_pdf(path: str, report_type: str, ranking: list[dict], recommendations: list[Recommendation]) -> None:
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Rapport GeoPulse — {report_type}", styles["Title"]), Spacer(1, 12)]

    table_data = [["Zone", "Score", "Revenu", "Points", "Tendance"]]
    table_data += [[r["zone"], r["score"], r["revenue"], r["points_count"], r["trend"]] for r in ranking]
    table = Table(table_data)
    table.setStyle(_TABLE_HEADER_STYLE)
    elements.append(table)

    if report_type == "Stratégique" and recommendations:
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Recommandations", styles["Heading2"]))
        rec_data = [["Zone", "Titre", "Urgence", "Potentiel"]]
        rec_data += [[r.zone, r.title, r.urgency, r.potential] for r in recommendations]
        rec_table = Table(rec_data)
        rec_table.setStyle(_TABLE_HEADER_STYLE)
        elements.append(rec_table)

    doc.build(elements)


def run_generate_report(db: Session, report: Report) -> Report:
    try:
        ranking = _filter_ranking(compute_zone_ranking(db), report.zones)
        recommendations = db.query(Recommendation).all() if report.type == "Stratégique" else []

        ext = "pdf" if report.format == "pdf" else "xlsx"
        filename = f"{report.id}.{ext}"
        path = os.path.join(REPORTS_DIR, filename)

        if report.format == "pdf":
            _write_pdf(path, report.type, ranking, recommendations)
        else:
            _write_xlsx(path, report.type, ranking, recommendations)

        report.status = "ready"
        report.file_path = path
        report.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)

        create_notification(
            db,
            title="Rapport disponible",
            message=f"Le rapport {report.type} ({report.format.upper()}) est prêt à être téléchargé.",
            type="report",
            priority="normal",
        )
    except Exception as exc:
        db.rollback()
        report.status = "failed"
        report.error_message = str(exc)
        report.finished_at = datetime.now(timezone.utc)
        db.commit()

    return report