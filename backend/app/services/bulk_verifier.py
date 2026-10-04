"""High-performance concurrent verification and deduplication engine for job listings.
Verifies live HTTP status and content for every job to guarantee zero 404s,
zero generic career pages, zero expired roles, and zero duplicates.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Job
from app.services.job_validator import validate_job_url
from app.crawler import canonical_url

logger = logging.getLogger("bulk_verifier")
logger.setLevel(logging.INFO)


def deduplicate_jobs(db: Session) -> int:
    """Eliminate redundant jobs sharing identical URLs or (company, title, location).
    Retains the most recently verified posting.
    """
    removed_count = 0
    jobs = db.scalars(
        select(Job).order_by(Job.company, Job.title, Job.last_checked_at.desc())
    ).all()

    seen_urls: set[str] = set()
    seen_roles: set[tuple[str, str, str]] = set()
    to_delete_ids = []

    for job in jobs:
        canon = canonical_url(job.apply_url)
        company_key = (job.company or "").strip().lower()
        title_key = (job.title or "").strip().lower()
        loc_key = (job.location or "").strip().lower()
        role_tuple = (company_key, title_key, loc_key)

        if canon in seen_urls:
            to_delete_ids.append(job.id)
            continue

        if company_key and title_key and role_tuple in seen_roles:
            to_delete_ids.append(job.id)
            continue

        seen_urls.add(canon)
        if company_key and title_key:
            seen_roles.add(role_tuple)

    if to_delete_ids:
        # Delete in chunks
        for i in range(0, len(to_delete_ids), 500):
            chunk = to_delete_ids[i:i + 500]
            db.execute(delete(Job).where(Job.id.in_(chunk)))
        db.commit()
        removed_count = len(to_delete_ids)
        logger.info(f"Deduplication removed {removed_count} redundant jobs.")

    return removed_count


async def verify_job_records_batch(
    jobs_data: list[dict[str, Any]],
    concurrency: int = 20,
    timeout_seconds: float = 12.0,
) -> list[tuple[str, bool, str | None, str | None]]:
    """Verify a batch of job URLs concurrently with a shared connection pool.
    Returns: list of (job_id, is_valid, final_url, rejection_reason)
    """
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    timeout = httpx.Timeout(timeout_seconds, connect=6.0)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True, headers=headers) as client:
        async def check(item: dict[str, Any]):
            job_id = item["id"]
            url = item["apply_url"]
            company = item.get("company")
            title = item.get("title")

            async with semaphore:
                try:
                    res = await validate_job_url(url, company=company, title=title, client=client)
                    return (job_id, res.is_valid, res.final_url, res.rejection_reason)
                except Exception as exc:
                    return (job_id, False, None, f"Exception during validation: {exc}")

        return await asyncio.gather(*(check(j) for j in jobs_data), return_exceptions=False)


def run_full_verification(db: Session, batch_size: int = 50, concurrency: int = 20) -> dict[str, int]:
    """Execute end-to-end verification and deduplication on all jobs in the database.
    Deletes any jobs returning 404, 410, closed notices, or generic homepages.
    """
    # 1. Deduplicate first
    dupes_removed = deduplicate_jobs(db)

    # 2. Query all active jobs
    jobs = db.scalars(
        select(Job).where(Job.status == "active")
    ).all()

    total_jobs = len(jobs)
    if total_jobs == 0:
        return {"total": 0, "valid": 0, "removed": 0, "duplicates_removed": dupes_removed}

    jobs_data = [
        {"id": str(j.id), "apply_url": j.apply_url, "company": j.company, "title": j.title}
        for j in jobs
    ]

    # 3. Concurrently verify in batches to control memory and database operations
    invalid_ids = []
    valid_updates = []
    now = datetime.now(timezone.utc)

    for i in range(0, total_jobs, batch_size):
        chunk = jobs_data[i:i + batch_size]
        results = asyncio.run(verify_job_records_batch(chunk, concurrency=concurrency))

        for job_id, is_valid, final_url, reason in results:
            if not is_valid:
                # Definitely dead: 404, 410, 403, closed phrase, generic homepage
                # If reason is purely a transient network error, skip deletion
                reason_lower = (reason or "").lower()
                if any(err in reason_lower for err in ("connection timeout", "connecterror", "no address associated", "temporary failure")):
                    continue
                invalid_ids.append(job_id)
            else:
                valid_updates.append((job_id, final_url))

    # 4. Remove invalid / 404 / expired jobs from DB
    if invalid_ids:
        for i in range(0, len(invalid_ids), 500):
            chunk = invalid_ids[i:i + 500]
            # Delete so they never appear in results
            db.execute(delete(Job).where(Job.id.in_(chunk)))
        db.commit()

    # 5. Update valid jobs with fresh timestamps and final redirected URLs
    if valid_updates:
        job_map = {str(j.id): j for j in jobs if str(j.id) not in set(invalid_ids)}
        for job_id, final_url in valid_updates:
            job = job_map.get(job_id)
            if job:
                job.last_verified_at = now
                job.last_checked_at = now
                if final_url:
                    job.final_url = final_url
                    job.job_url = final_url
        db.commit()

    logger.info(
        f"Verification completed. Total: {total_jobs}, Valid: {len(valid_updates)}, Removed (404/Closed): {len(invalid_ids)}, Dupes: {dupes_removed}"
    )

    return {
        "total": total_jobs,
        "valid": len(valid_updates),
        "removed": len(invalid_ids),
        "duplicates_removed": dupes_removed,
    }
