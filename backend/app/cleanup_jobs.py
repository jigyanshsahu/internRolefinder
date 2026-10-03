"""Unified cleanup, deduplication, and expiration script for InternRoleFinder.

1. Schema validation: Ensures all tracking and validation columns exist in the database.
2. Unnecessary jobs removal: Removes any jobs that violate the strict anti-senior and role classifier rules.
3. Duplicate jobs removal:
   - Detects URL parameter/casing variations (e.g. ?embed=true, ?gh_jid=..., case differences) and removes duplicates.
   - Detects semantic duplicates (same company, normalized role, and location) and retains only the single cleanest posting.
4. Job Expiration:
   - Validates live HTTP status and page content for all remaining postings.
   - Marks closed, 404, 410, 403, or stale jobs with status="expired".
   - Updates verified active jobs with status="active" and refreshed verification timestamps.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from sqlalchemy import inspect, select, text

from app.classifier import classify_role
from app.crawler import canonical_url
from app.database import SessionLocal, engine
from app.models import Job
from app.services.job_validator import is_generic_careers_url, validate_job_url

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cleanup_jobs")


def run_database_migrations() -> None:
    """Ensure all required columns and indices exist on the jobs table."""
    logger.info("Checking database schema and ensuring required columns exist...")
    inspector = inspect(engine)
    job_columns = {column["name"] for column in inspector.get_columns("jobs")}

    with engine.begin() as connection:
        if "source" not in job_columns:
            logger.info("Adding column 'source' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN source VARCHAR(100)"))
        if "source_job_id" not in job_columns:
            logger.info("Adding column 'source_job_id' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN source_job_id VARCHAR(255)"))
        if "original_url" not in job_columns:
            logger.info("Adding column 'original_url' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN original_url TEXT"))
        if "job_url" not in job_columns:
            logger.info("Adding column 'job_url' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN job_url TEXT"))
        if "final_url" not in job_columns:
            logger.info("Adding column 'final_url' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN final_url TEXT"))
        if "status" not in job_columns:
            logger.info("Adding column 'status' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'active'"))
        if "last_verified_at" not in job_columns:
            logger.info("Adding column 'last_verified_at' to jobs table")
            connection.execute(text("ALTER TABLE jobs ADD COLUMN last_verified_at TIMESTAMP WITH TIME ZONE"))

        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_source ON jobs(source)"))


def normalize_clean_url(url: str) -> str:
    """Canonicalize a job URL by stripping cosmetic tracking query parameters and standardizing path casing."""
    if not url:
        return ""
    p = urlsplit(url)
    scheme = p.scheme.lower() or "https"
    netloc = p.netloc.lower()
    path = p.path.rstrip("/")

    # Lowercase path for common ATS platforms where company slug is in path
    if any(ats in netloc for ats in ("ashbyhq.com", "smartrecruiters.com", "greenhouse.io", "lever.co")):
        path = path.lower()

    ignored_params = {"embed", "ref", "source", "gh_src", "ats", "mode", "iis", "iisn", "t"}
    clean_params = []
    for k, v in parse_qsl(p.query):
        k_lower = k.lower()
        if k_lower.startswith("utm_") or k_lower in ignored_params:
            continue
        clean_params.append((k, v))

    clean_params.sort()
    query = urlencode(clean_params)
    return urlunsplit((scheme, netloc, path, query, ""))


def norm_company(c: str | None) -> str:
    c = (c or "").lower()
    c = re.sub(r"(\binc\b|\bllc\b|\bcorp\b|\btechnologies\b|\btechnology\b|\bgroup\b)", "", c)
    return " ".join(re.sub(r"[^a-z0-9]", " ", c).split())


def norm_title(s: str | None) -> str:
    t = (s or "").lower()
    t = re.sub(r"\b(summer|winter|spring|fall|autumn)\s*(202[4-9])?\b", "", t)
    t = re.sub(r"\b(internship|interns)\b", "intern", t)
    return " ".join(re.sub(r"[^a-z0-9]", " ", t).split())


def norm_location(loc: str | None) -> str:
    l = (loc or "").lower()
    l = re.sub(r"\b[0-9]{4,5}(-[0-9]{4})?\b", "", l)
    l = re.sub(r"[^a-z]", " ", l)
    return " ".join(l.split())


async def deduplicate_and_expire_jobs() -> dict[str, Any]:
    """Execute deduplication of unnecessary duplicate jobs and expire stale/closed postings."""
    db = SessionLocal()
    try:
        all_jobs = db.scalars(select(Job)).all()
        initial_count = len(all_jobs)
        logger.info(f"Loaded {initial_count} total jobs from database.")

        to_delete_ids: set[Any] = set()
        unnecessary_count = 0
        url_dup_count = 0
        semantic_dup_count = 0

        # Phase 1: Identify unclassifiable / senior / invalid roles
        for j in all_jobs:
            if not classify_role(j.title):
                to_delete_ids.add(j.id)
                unnecessary_count += 1

        logger.info(f"Identified {unnecessary_count} unclassifiable or senior roles for removal.")

        # Phase 2: Identify URL variations duplicates
        from collections import defaultdict
        url_groups: dict[str, list[Job]] = defaultdict(list)
        for j in all_jobs:
            if j.id in to_delete_ids:
                continue
            norm_u = normalize_clean_url(j.apply_url)
            url_groups[norm_u].append(j)

        for norm_u, jlist in url_groups.items():
            if len(jlist) > 1:
                # Keep the cleanest, most descriptive job entry
                jlist.sort(key=lambda x: (
                    not x.apply_url.startswith("https://internrolefinder.internal"),
                    x.last_verified_at is not None,
                    len(x.title or ""),
                ), reverse=True)
                for dup in jlist[1:]:
                    to_delete_ids.add(dup.id)
                    url_dup_count += 1

        logger.info(f"Identified {url_dup_count} URL variation duplicates for removal.")

        # Phase 3: Identify Semantic duplicate postings (exact same company, normalized title, location)
        semantic_groups: dict[tuple[str, str, str], list[Job]] = defaultdict(list)
        for j in all_jobs:
            if j.id in to_delete_ids:
                continue
            key = (norm_company(j.company), norm_title(j.title), norm_location(j.location))
            semantic_groups[key].append(j)

        for key, jlist in semantic_groups.items():
            if len(jlist) > 1:
                jlist.sort(key=lambda x: (
                    not x.apply_url.startswith("https://internrolefinder.internal"),
                    x.last_verified_at is not None,
                    len(x.title or ""),
                ), reverse=True)
                for dup in jlist[1:]:
                    to_delete_ids.add(dup.id)
                    semantic_dup_count += 1

        logger.info(f"Identified {semantic_dup_count} semantic duplicate roles for removal.")
        logger.info(f"Total duplicate & unnecessary jobs marked for removal: {len(to_delete_ids)}")

        # Delete duplicates from DB
        for j in all_jobs:
            if j.id in to_delete_ids:
                db.delete(j)
        db.commit()
        logger.info("Successfully deleted duplicate and unnecessary job rows from database.")

        # Phase 4: Validate remaining jobs and expire stale/closed postings
        remaining_jobs = db.scalars(select(Job)).all()
        logger.info(f"Running live validation across {len(remaining_jobs)} remaining jobs...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        semaphore = asyncio.Semaphore(20)

        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers=headers) as client:
            async def validate_job(job: Job):
                async with semaphore:
                    res = await validate_job_url(
                        url=job.apply_url,
                        company=job.company,
                        title=job.title,
                        client=client,
                    )
                    return job, res

            results = await asyncio.gather(*[validate_job(j) for j in remaining_jobs])

        now = datetime.now(timezone.utc)
        expired_count = 0
        active_count = 0
        valid_jobs_to_canonicalize: list[tuple[Job, str]] = []

        for job, res in results:
            if not res.is_valid or res.http_status == 403 or res.status == "error_403":
                db.delete(job)
                expired_count += 1
            else:
                final_clean = normalize_clean_url(res.final_url or job.apply_url)
                job.status = "active"
                job.source = res.source or job.source
                job.source_job_id = res.source_job_id or job.source_job_id
                job.last_verified_at = now
                job.last_checked_at = now
                valid_jobs_to_canonicalize.append((job, final_clean))
                active_count += 1

        db.commit()
        logger.info(f"Expired {expired_count} stale/closed jobs.")

        # Phase 5: Safely canonicalize active job URLs to prevent unique collision
        # Assign temporary distinct URLs first
        for job, _ in valid_jobs_to_canonicalize:
            job.apply_url = f"https://internrolefinder.internal/temp/{job.id}"
        db.flush()

        # Check for any collision on final_clean URL among active jobs
        active_seen_urls = set()
        for job, final_clean in valid_jobs_to_canonicalize:
            if final_clean in active_seen_urls:
                # Duplicate resolved after redirect
                job.status = "expired"
                expired_count += 1
                active_count -= 1
            else:
                active_seen_urls.add(final_clean)
                job.apply_url = final_clean
                job.job_url = final_clean
                job.final_url = final_clean

        db.commit()
        logger.info(f"Canonicalized URLs for {len(active_seen_urls)} active jobs.")

        # Re-fetch final active jobs for reporting
        final_active_jobs = db.scalars(select(Job).where(Job.status == "active")).all()

        return {
            "initial_total": initial_count,
            "unnecessary_senior_removed": unnecessary_count,
            "url_duplicates_removed": url_dup_count,
            "semantic_duplicates_removed": semantic_dup_count,
            "total_duplicates_removed": len(to_delete_ids),
            "jobs_expired": expired_count,
            "active_unique_jobs_remaining": len(final_active_jobs),
            "sample_active_jobs": [
                {
                    "company": j.company,
                    "title": j.title,
                    "location": j.location,
                    "apply_url": j.apply_url,
                    "source": j.source,
                }
                for j in final_active_jobs[:10]
            ],
        }
    finally:
        db.close()


def main():
    run_database_migrations()
    summary = asyncio.run(deduplicate_and_expire_jobs())

    logger.info("=" * 60)
    logger.info("CLEANUP, DEDUPLICATION & EXPIRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Initial jobs in database: {summary['initial_total']}")
    logger.info(f"Unnecessary / senior roles removed: {summary['unnecessary_senior_removed']}")
    logger.info(f"URL variation duplicates removed: {summary['url_duplicates_removed']}")
    logger.info(f"Semantic duplicates removed: {summary['semantic_duplicates_removed']}")
    logger.info(f"Total duplicates removed: {summary['total_duplicates_removed']}")
    logger.info(f"Stale / closed jobs expired: {summary['jobs_expired']}")
    logger.info(f"Active unique verified jobs remaining: {summary['active_unique_jobs_remaining']}")
    logger.info("-" * 60)
    logger.info("SAMPLE ACTIVE JOBS:")
    for idx, j in enumerate(summary["sample_active_jobs"], 1):
        logger.info(f"{idx}. [{j['company']}] {j['title']} ({j['location']})")
        logger.info(f"   URL: {j['apply_url']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
