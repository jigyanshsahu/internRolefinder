import asyncio
import logging
from datetime import datetime, timedelta, timezone
from celery import Celery
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from app.config import get_settings
from app.crawler import canonical_url, discover_company_boards, discover_indian_startup_boards, discover_jobs_from_public_ats, is_active
from app.database import SessionLocal
from app.models import CompanySeed, Job, StartupBoard

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

settings = get_settings()
celery_app = Celery("internrolefinder", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.beat_schedule = {
    "discover-jobs": {"task": "app.worker.discover_jobs", "schedule": settings.crawl_interval_minutes * 60},
    "discover-company-seeds": {"task": "app.worker.discover_company_seeds", "schedule": settings.startup_discovery_interval_hours * 60 * 60},
    "verify-jobs": {"task": "app.worker.verify_jobs", "schedule": settings.verify_interval_minutes * 60},
    "expire-stale-jobs": {"task": "app.worker.expire_stale_jobs", "schedule": settings.verify_interval_minutes * 60},
}
celery_app.conf.timezone = "UTC"


def purge_stale_jobs(db, cutoff: datetime) -> int:
    result = db.execute(delete(Job).where(Job.last_checked_at < cutoff))
    return max(result.rowcount or 0, 0)


def _upsert_discovered_jobs(db, discovered_jobs) -> int:
    rows_by_url = {}
    for job in discovered_jobs:
        apply_url = canonical_url(job.apply_url)
        rows_by_url.setdefault(apply_url, {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "country": job.country,
            "is_remote": job.is_remote,
            "role_type": job.role_type,
            "apply_url": apply_url,
            "source_url": job.source_url,
        })
    if not rows_by_url:
        return 0

    known_urls = set(db.scalars(select(Job.apply_url).where(Job.apply_url.in_(rows_by_url))).all())
    statement = postgres_insert(Job).values(list(rows_by_url.values()))
    excluded = statement.excluded
    statement = statement.on_conflict_do_update(
        index_elements=[Job.apply_url],
        set_={
            "last_checked_at": func.now(),
            "role_type": excluded.role_type,
            "location": func.coalesce(excluded.location, Job.location),
            "country": func.coalesce(excluded.country, Job.country),
            "is_remote": excluded.is_remote,
        },
    )
    db.execute(statement)
    return sum(apply_url not in known_urls for apply_url in rows_by_url)


@celery_app.task(name="app.worker.discover_jobs")
def discover_jobs() -> int:
    db = SessionLocal()
    try:
        startup_boards = [
            {"name": board.company_name, "platform": board.platform, "slug": board.slug, "careers_url": board.careers_url}
            for board in db.scalars(select(StartupBoard)).all()
        ]
        discovered = _upsert_discovered_jobs(
            db,
            asyncio.run(discover_jobs_from_public_ats(startup_boards)),
        )
        db.commit()
    finally:
        db.close()
    return discovered


@celery_app.task(name="app.worker.discover_company_seeds")
def discover_company_seeds() -> int:
    db = SessionLocal()
    try:
        seeds = db.scalars(select(CompanySeed).where(CompanySeed.enabled.is_(True))).all()
        companies = [
            {
                "company_name": seed.company_name,
                "website_url": seed.website_url,
                "careers_url": seed.careers_url,
            }
            for seed in seeds
        ]
        results = asyncio.run(discover_company_boards(companies))
        seed_by_name = {seed.company_name: seed for seed in seeds}
        boards_by_key = {
            (board.platform, board.slug): board
            for board in db.scalars(select(StartupBoard)).all()
        }
        discovered = 0
        found_boards = 0
        checked_at = datetime.now(timezone.utc)
        for result in results:
            seed = seed_by_name[result.company_name]
            seed.status = result.status
            seed.last_checked_at = checked_at
            seed.last_error = None
            if not result.board:
                continue
            found_boards += 1
            key = (result.board.platform, result.board.slug)
            board = boards_by_key.get(key)
            if board:
                board.company_name = result.board.company_name
                board.careers_url = result.board.careers_url
                continue
            board = StartupBoard(
                company_name=result.board.company_name,
                platform=result.board.platform,
                slug=result.board.slug,
                careers_url=result.board.careers_url,
            )
            db.add(board)
            boards_by_key[key] = board
            discovered += 1
        db.commit()
    finally:
        db.close()
    if found_boards:
        discover_jobs.delay()
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
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    db = SessionLocal()
    try:
        removed = purge_stale_jobs(db, cutoff)
        for job in db.scalars(select(Job)).all():
            active = asyncio.run(is_active(job.apply_url))
            if active is None:
                continue
            if active:
                job.last_checked_at = datetime.now(timezone.utc)
            else:
                db.delete(job)
                removed += 1
        db.commit()
    finally:
        db.close()
    return removed


@celery_app.task(name="app.worker.expire_stale_jobs")
def expire_stale_jobs() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    db = SessionLocal()
    try:
        removed = purge_stale_jobs(db, cutoff)
        db.commit()
        return removed
    finally:
        db.close()
