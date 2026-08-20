# app/services/decision.py
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.datapoint import DataPoint
from app.models.recommendation import Recommendation
from app.services.notifications import create_notification

TREND_WINDOW_DAYS = 30

# TODO : une fois la synchronisation mobility_trips en production, enrichir le
# scoring par zone avec les trajets dont la route passe par le polygone de la
# zone (Zone.boundary). Nécessite un calcul géospatial non implémenté ici —
# ranking et recommandations reposent pour l'instant uniquement sur DataPoint.


def _zone_trend(db: Session, zone: str) -> str:
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=TREND_WINDOW_DAYS)
    previous_cutoff = now - timedelta(days=2 * TREND_WINDOW_DAYS)

    recent_avg = (
        db.query(func.coalesce(func.avg(DataPoint.score), 0))
        .filter(DataPoint.zone == zone, DataPoint.created_at >= recent_cutoff)
        .scalar()
    )
    previous_avg = (
        db.query(func.coalesce(func.avg(DataPoint.score), 0))
        .filter(
            DataPoint.zone == zone,
            DataPoint.created_at >= previous_cutoff,
            DataPoint.created_at < recent_cutoff,
        )
        .scalar()
    )

    recent_avg = float(recent_avg or 0)
    previous_avg = float(previous_avg or 0)

    if previous_avg == 0:
        return "stable"
    delta = recent_avg - previous_avg
    if delta > 2:
        return "hausse"
    if delta < -2:
        return "baisse"
    return "stable"


def compute_zone_ranking(db: Session) -> list[dict]:
    rows = (
        db.query(
            DataPoint.zone,
            func.coalesce(func.avg(DataPoint.score), 0).label("score"),
            func.coalesce(func.sum(DataPoint.revenue), 0).label("revenue"),
            func.count(DataPoint.id).label("points_count"),
        )
        .group_by(DataPoint.zone)
        .all()
    )

    ranking = [
        {
            "zone": zone,
            "score": round(float(score), 1),
            "revenue": round(float(revenue), 2),
            "points_count": points_count,
            "trend": _zone_trend(db, zone),
        }
        for zone, score, revenue, points_count in rows
    ]

    ranking.sort(key=lambda item: (item["score"], item["revenue"]), reverse=True)
    return ranking


def _generate_recommendations(db: Session, ranking: list[dict]) -> None:
    db.query(Recommendation).delete()

    for item in ranking:
        if item["trend"] == "baisse" and item["revenue"] > 0:
            db.add(Recommendation(
                zone=item["zone"],
                title=f"Zone {item['zone']} en baisse",
                message=(
                    f"Le score moyen de la zone {item['zone']} est en baisse sur les "
                    f"{TREND_WINDOW_DAYS} derniers jours malgré un revenu de {item['revenue']}. "
                    "Une attention particulière est recommandée."
                ),
                urgency="high",
                potential=max(0, 100 - int(item["score"])),
            ))
        elif item["score"] >= 70 and item["points_count"] >= 5:
            db.add(Recommendation(
                zone=item["zone"],
                title=f"Zone {item['zone']} à fort potentiel",
                message=(
                    f"La zone {item['zone']} affiche un score moyen élevé ({item['score']}) "
                    f"sur {item['points_count']} points. Zone à prioriser."
                ),
                urgency="normal",
                potential=int(item["score"]),
            ))

    db.commit()


def run_generate_analysis(db: Session, job: AnalysisJob) -> AnalysisJob:
    try:
        ranking = compute_zone_ranking(db)
        _generate_recommendations(db, ranking)

        job.status = "success"
        job.zones_processed = len(ranking)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        create_notification(
            db,
            title="Analyse terminée",
            message=f"Le recalcul du scoring est terminé pour {len(ranking)} zone(s).",
            type="analysis",
            priority="normal",
        )
    except Exception as exc:
        db.rollback()
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    return job