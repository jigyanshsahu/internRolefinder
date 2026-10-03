"""Ingest and validate new software internship jobs into the database.

All candidate jobs are strictly filtered to exclude any senior, lead, staff, principal,
manager, director, architect, or non-intern roles.
Every candidate URL is validated using `validate_job_url` before being stored.
Any jobs that are stale, closed, redirect to generic careers pages, or return HTTP 404/410/403 are rejected.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from app.classifier import classify_role
from app.config import get_settings
from app.crawler import (
    ExtractedJob,
    canonical_url,
    discover_jobs_from_public_ats,
    discover_jobs_from_verified_listings,
    get_ats_name,
    is_startup_company,
)
from app.database import SessionLocal
from app.models import Job, StartupBoard
from app.services.job_validator import is_generic_careers_url, validate_job_url

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("add_more_jobs")


async def fetch_resumax_candidates() -> list[ExtractedJob]:
    """Fetch recent software internships from ResuMax tech-internships tracker."""
    url = "https://raw.githubusercontent.com/resumax/tech-internships/main/README.md"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            lines = [l for l in r.text.splitlines() if l.startswith("| **")]
    except Exception as e:
        print(f"Error fetching ResuMax: {e}")
        return []

    jobs: list[ExtractedJob] = []
    for l in lines:
        parts = l.split("|")
        if len(parts) >= 5:
            comp_m = re.search(r"\*\*\[(.*?)\]", parts[1])
            company = comp_m.group(1) if comp_m else parts[1].strip("* ")
            title = parts[2].strip()
            location = parts[3].strip()
            url_m = re.search(r"\[Apply\]\((https?://.*?)\)", parts[4])
            apply_url = url_m.group(1) if url_m else None
            if not apply_url:
                continue
            is_gen, _ = is_generic_careers_url(apply_url)
            if is_gen:
                continue
            role = classify_role(title)
            if not role:
                continue
            canon = canonical_url(apply_url)
            jobs.append(ExtractedJob(
                title=title[:500],
                company=company[:300] if company else None,
                location=location[:300] if location else None,
                country=None,
                is_remote=bool(re.search(r"\bremote\b", location, re.I)),
                is_startup=is_startup_company(company, canon, canon),
                role_type=role,
                apply_url=canon,
                source_url=canon,
                source=get_ats_name(canon).lower(),
                job_url=canon,
                final_url=canon,
                original_url=canon,
            ))
    return jobs


async def fetch_speedyapply_candidates() -> list[ExtractedJob]:
    """Fetch software internships from SpeedyApply SWE college jobs tracker."""
    url = "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            lines = [l for l in r.text.splitlines() if "|" in l and "href" in l]
    except Exception as e:
        print(f"Error fetching SpeedyApply: {e}")
        return []

    jobs: list[ExtractedJob] = []
    for l in lines:
        parts = l.split("|")
        if len(parts) >= 6:
            comp_m = re.search(r"<strong>(.*?)</strong>", parts[1])
            company = comp_m.group(1) if comp_m else parts[1].strip()
            title = parts[2].strip()
            location = parts[3].strip()
            url_m = re.search(r'href="(https?://[^"]+)"', parts[5])
            apply_url = url_m.group(1) if url_m else None
            if not apply_url:
                continue
            is_gen, _ = is_generic_careers_url(apply_url)
            if is_gen:
                continue
            role = classify_role(title)
            if not role:
                continue
            canon = canonical_url(apply_url)
            jobs.append(ExtractedJob(
                title=title[:500],
                company=company[:300] if company else None,
                location=location[:300] if location else None,
                country=None,
                is_remote=bool(re.search(r"\bremote\b", location, re.I)),
                is_startup=is_startup_company(company, canon, canon),
                role_type=role,
                apply_url=canon,
                source_url=canon,
                source=get_ats_name(canon).lower(),
                job_url=canon,
                final_url=canon,
                original_url=canon,
            ))
    return jobs


async def run_add_more_jobs(concurrency: int = 15):
    print("=" * 70)
    print("STARTING VALIDATED INTERNSHIP INGESTION PIPELINE")
    print("RULE: STRICTLY ZERO SENIOR / LEAD / EXPERIENCED JOBS")
    print("RULE: ONLY ACTIVE INTERNSHIPS WITH EXACT POSTING URLS")
    print("=" * 70)

    db = SessionLocal()
    try:
        initial_count = db.scalar(select(func.count(Job.id)).where(Job.status == "active"))
        existing_urls = set(db.scalars(select(Job.apply_url)).all())
        existing_orig_urls = set(db.scalars(select(Job.original_url).where(Job.original_url.isnot(None))).all())
        known_urls = existing_urls | existing_orig_urls
        print(f"Current active jobs in database: {initial_count}")
        print(f"Total known URLs in database: {len(known_urls)}")

        # Step 1: Discover candidate jobs across multiple primary sources
        print("\nStep 1: Gathering candidate jobs across verified sources and public ATS feeds...")
        
        # 1. SimplifyJobs verified listings
        simplify_candidates = await discover_jobs_from_verified_listings(limit=25000)
        print(f" -> Gathered {len(simplify_candidates)} software intern roles from SimplifyJobs.")

        # 2. ResuMax tech internships
        resumax_candidates = await fetch_resumax_candidates()
        print(f" -> Gathered {len(resumax_candidates)} software intern roles from ResuMax.")

        # 3. SpeedyApply college SWE jobs
        speedy_candidates = await fetch_speedyapply_candidates()
        print(f" -> Gathered {len(speedy_candidates)} software intern roles from SpeedyApply.")

        all_candidates = simplify_candidates + resumax_candidates + speedy_candidates
        print(f"Total raw candidates collected: {len(all_candidates)}")

        # Step 2: Strictly filter candidates
        # - Must classify as a software internship
        # - Deduplicate and skip already known URLs
        unique_candidates = {}
        for c in all_candidates:
            # Extra strict senior check
            if classify_role(c.title) is None:
                continue
            canon = canonical_url(c.apply_url)
            is_gen, _ = is_generic_careers_url(canon)
            if is_gen:
                continue
            if canon in known_urls:
                continue
            unique_candidates.setdefault(canon, c)

        candidates_to_validate = list(unique_candidates.values())
        print(f"\nFiltered candidate pool to validate: {len(candidates_to_validate)} brand-new URLs")

        if not candidates_to_validate:
            print("No new candidates found to validate. Database is already fully up to date.")
            return

        # Step 3: Validate each candidate concurrently
        print(f"\nStep 2: Concurrently validating candidate URLs (concurrency={concurrency})...")
        print("Each URL will follow redirects, verify individual posting, and check active status.\n")

        semaphore = asyncio.Semaphore(concurrency)
        stats = {
            "checked": 0,
            "valid": 0,
            "generic_careers": 0,
            "expired_closed": 0,
            "http_error": 0,
            "other_invalid": 0,
        }
        validated_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
            async def validate_candidate(candidate):
                async with semaphore:
                    stats["checked"] += 1
                    res = await validate_job_url(
                        candidate.apply_url,
                        company=candidate.company,
                        title=candidate.title,
                        client=client,
                    )
                    if res.is_valid and res.final_url:
                        stats["valid"] += 1
                        validated_jobs.append((candidate, res))
                    else:
                        if res.status == "generic_careers":
                            stats["generic_careers"] += 1
                        elif res.status in ("stale", "expired"):
                            stats["expired_closed"] += 1
                        elif res.status in ("http_error", "not_individual_job"):
                            stats["http_error"] += 1
                        else:
                            stats["other_invalid"] += 1

            await asyncio.gather(*(validate_candidate(c) for c in candidates_to_validate), return_exceptions=True)

        print("\n" + "=" * 70)
        print("VALIDATION RESULTS")
        print("=" * 70)
        print(f"Total candidates checked:       {stats['checked']}")
        print(f"Valid active jobs confirmed:    {stats['valid']}")
        print(f"Generic career pages rejected:  {stats['generic_careers']}")
        print(f"Expired/closed pages rejected:  {stats['expired_closed']}")
        print(f"HTTP errors/other rejected:     {stats['http_error'] + stats['other_invalid']}")
        print("=" * 70)

        # Step 4: Insert validated jobs into the database
        print("\nStep 3: Storing validated jobs in database...")
        rows_by_final_url = {}
        for candidate, res in validated_jobs:
            final_url = canonical_url(res.final_url)
            if final_url in existing_urls:
                continue

            rows_by_final_url.setdefault(final_url, {
                "title": candidate.title,
                "company": candidate.company,
                "location": candidate.location,
                "country": candidate.country,
                "is_remote": candidate.is_remote,
                "is_startup": candidate.is_startup,
                "description": candidate.description,
                "posted_at": candidate.posted_at,
                "role_type": candidate.role_type,
                "apply_url": final_url,
                "source_url": candidate.source_url,
                "source": res.source or candidate.source or get_ats_name(final_url).lower(),
                "source_job_id": res.source_job_id or candidate.source_job_id,
                "original_url": candidate.apply_url,
                "job_url": final_url,
                "final_url": final_url,
                "status": "active",
                "last_verified_at": func.now(),
                "last_checked_at": func.now(),
            })

        if rows_by_final_url:
            values_to_insert = list(rows_by_final_url.values())
            stmt = postgres_insert(Job).values(values_to_insert)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[Job.apply_url],
                set_={
                    "last_checked_at": func.now(),
                    "last_verified_at": func.now(),
                    "status": "active",
                    "source": func.coalesce(excluded.source, Job.source),
                    "source_job_id": func.coalesce(excluded.source_job_id, Job.source_job_id),
                    "job_url": func.coalesce(excluded.job_url, Job.job_url),
                    "final_url": func.coalesce(excluded.final_url, Job.final_url),
                    "role_type": excluded.role_type,
                    "location": func.coalesce(excluded.location, Job.location),
                    "country": func.coalesce(excluded.country, Job.country),
                    "is_remote": excluded.is_remote,
                    "is_startup": func.coalesce(excluded.is_startup, Job.is_startup),
                    "description": func.coalesce(excluded.description, Job.description),
                    "posted_at": func.coalesce(excluded.posted_at, Job.posted_at),
                },
            )
            db.execute(stmt)
            db.commit()
            print(f"Successfully upserted {len(values_to_insert)} validated jobs into the database.")
        else:
            print("No new jobs to insert.")

        final_count = db.scalar(select(func.count(Job.id)).where(Job.status == "active"))
        new_added = final_count - initial_count
        print(f"\nPrevious active jobs: {initial_count}")
        print(f"Total active jobs now: {final_count} (+{new_added} new active jobs added)")

        # Step 5: Sample verification of newly added jobs
        print("\n" + "=" * 70)
        print("SAMPLE VERIFICATION OF REMAINING ACTIVE JOBS (25 SAMPLE)")
        print("=" * 70)
        sample_jobs = db.scalars(
            select(Job)
            .where(Job.status == "active")
            .order_by(Job.last_verified_at.desc(), Job.id.desc())
            .limit(25)
        ).all()

        for idx, j in enumerate(sample_jobs, 1):
            print(f"[{idx:02d}] {j.company or 'Unknown'} | {j.title}")
            print(f"     Source: {j.source or 'direct'} | Job ID: {j.source_job_id or 'N/A'}")
            print(f"     URL: {j.apply_url}")
            print(f"     Status: {j.status} | Last Verified: {j.last_verified_at}")
            print("-" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_add_more_jobs(concurrency=15))
