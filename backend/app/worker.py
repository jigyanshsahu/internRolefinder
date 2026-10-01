import asyncio
import logging
from datetime import datetime, timezone
from celery import Celery
from sqlalchemy import select
from app.config import get_settings
from app.crawler import canonical_url, discover_indian_startup_boards, discover_jobs_from_public_ats, is_active
from app.database import SessionLocal
from app.models import Job, StartupBoard

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

settings = get_settings()
celery_app = Celery("internrolefinder", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.beat_schedule = {
    "discover-jobs": {"task": "app.worker.discover_jobs", "schedule": settings.crawl_interval_minutes * 60},
    "discover-indian-startups": {"task": "app.worker.discover_indian_startups", "schedule": settings.startup_discovery_interval_hours * 60 * 60},
    "verify-jobs": {"task": "app.worker.verify_jobs", "schedule": settings.verify_interval_minutes * 60},
}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="app.worker.discover_jobs")
def discover_jobs() -> int:
    discovered = 0
    db = SessionLocal()
    try:
        startup_boards = [
            {"name": board.company_name, "platform": board.platform, "slug": board.slug}
            for board in db.scalars(select(StartupBoard)).all()
        ]
        for job in asyncio.run(discover_jobs_from_public_ats(startup_boards)):
            existing = db.scalar(select(Job).where(Job.apply_url == canonical_url(job.apply_url)))
            if existing:
                existing.last_checked_at = datetime.now(timezone.utc)
                existing.role_type = job.role_type
                if job.location is not None:
                    existing.location = job.location
                if job.country is not None:
                    existing.country = job.country
                existing.is_remote = job.is_remote
                continue
            db.add(Job(
                title=job.title,
                company=job.company,
                location=job.location,
                country=job.country,
                is_remote=job.is_remote,
                role_type=job.role_type,
                apply_url=canonical_url(job.apply_url),
                source_url=job.source_url,
            ))
            discovered += 1
        db.commit()
    finally:
        db.close()
    return discovered


@celery_app.task(name="app.worker.discover_indian_startups")
def discover_indian_startups() -> int:
    api_key = settings.gemini_api_key
    if not api_key or not api_key.get_secret_value().strip():
        return 0
    boards = asyncio.run(discover_indian_startup_boards())
    discovered = 0
    db = SessionLocal()
    try:
        for board in boards:
            existing = db.scalar(
                select(StartupBoard).where(
                    StartupBoard.platform == board.platform,
                    StartupBoard.slug == board.slug,
                )
            )
            if existing:
                existing.company_name = board.company_name
                existing.careers_url = board.careers_url
                continue
            db.add(StartupBoard(
                company_name=board.company_name,
                platform=board.platform,
                slug=board.slug,
                careers_url=board.careers_url,
            ))
            discovered += 1
        db.commit()
    finally:
        db.close()
    if discovered:
        discover_jobs.delay()
    return discovered


@celery_app.task(name="app.worker.verify_jobs")
def verify_jobs() -> int:
    removed = 0
    db = SessionLocal()
    try:
        for job in db.scalars(select(Job)).all():
            if asyncio.run(is_active(job.apply_url)):
                job.last_checked_at = datetime.now(timezone.utc)
            else:
                db.delete(job)
                removed += 1
        db.commit()
    finally:
        db.close()
    return removed
