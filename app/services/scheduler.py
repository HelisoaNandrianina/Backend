# app/services/scheduler.py
import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.services.sync import run_trip_sync

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _scheduler_loop() -> None:
    interval_seconds = settings.SYNC_INTERVAL_MINUTES * 60
    while True:
        await asyncio.sleep(interval_seconds)
        db = SessionLocal()
        try:
            await run_trip_sync(db, settings.SYNC_SOURCE_URL, "scheduled")
        finally:
            db.close()


def start_scheduler() -> None:
    global _task
    if _task is None:
        _task = asyncio.create_task(_scheduler_loop())
        logger.info("Sync scheduler started (interval: %s min)", settings.SYNC_INTERVAL_MINUTES)


async def stop_scheduler() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
        logger.info("Sync scheduler stopped")
