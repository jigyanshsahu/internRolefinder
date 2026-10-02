from datetime import datetime, timedelta, timezone
import re
from typing import Literal
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, case, func, inspect, or_, select, text
from sqlalchemy.orm import Session
from app.config import get_settings
from app.classifier import classify_role
from app.crawler import _board_url, canonical_url
from app.database import Base, SessionLocal, engine, get_db
from app.models import CompanySeed, Job, RoleType, StartupBoard
from app.schemas import CompanySeedOut, JobAlertsOut, JobOut, JobPageOut, SummaryOut
from app.worker import celery_app, purge_stale_jobs
from app.company_seeds import COMPANY_SEEDS

settings = get_settings()
app = FastAPI(title="InternRoleFinder API")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])


def _compute_fit(job: Job, skills_list: list[str], loc_pref: str | None, dates_pref: str | None) -> tuple[int, list[str]]:
    score = 60
    matched_skills: list[str] = []
    title_lower = (job.title or "").lower()
    desc_lower = (job.description or "").lower()
    content = f"{title_lower} {desc_lower}"

    if skills_list:
        found_count = 0
        for skill in skills_list:
            escaped = re.escape(skill)
            if re.search(rf"\b{escaped}\b", title_lower, re.I):
                score += 15
                found_count += 1
                matched_skills.append(skill)
            elif re.search(rf"\b{escaped}\b", desc_lower, re.I):
                score += 8
                found_count += 1
                matched_skills.append(skill)
        if not found_count:
            score -= 20
    else:
        score += 10

    if loc_pref:
        pref = loc_pref.lower()
        if pref in ("remote", "any_remote"):
            if job.is_remote:
                score += 20
            else:
                score -= 30
        elif pref in ("india", "india_tech"):
            if job.country == "India" or job.is_remote:
                score += 20
            else:
                score -= 15
        elif pref == "international":
            if job.is_remote or job.country != "India":
                score += 15
    else:
        if job.is_remote:
            score += 15
        elif job.country == "India":
            score += 10

    if dates_pref:
        pref = dates_pref.lower()
        if "summer" in pref:
            if any(term in content for term in ("summer", "may 2026", "june 2026", "july 2026")):
                score += 15
            else:
                score += 5
        elif "immediate" in pref or "fall" in pref:
            if any(term in content for term in ("immediate", "asap", "fall", "autumn", "august", "september")):
                score += 15
            else:
                score += 5
        elif "winter" in pref or "spring" in pref:
            if any(term in content for term in ("winter", "spring", "january", "2027")):
                score += 15
            else:
                score += 5
        elif pref in content:
            score += 15
    else:
        score += 5

    return min(max(score, 10), 100), matched_skills


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        for role_value in ("ai", "other"):
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TYPE role_type ADD VALUE IF NOT EXISTS '{role_value}'"))
    job_columns = {column["name"] for column in inspect(engine).get_columns("jobs")}
    with engine.begin() as connection:
        if "location" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN location VARCHAR(300)"))
        if "country" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN country VARCHAR(150)"))
        if "is_remote" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN is_remote BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("UPDATE jobs SET country = 'India' WHERE country IS NULL AND LOWER(COALESCE(location, '')) LIKE '%india%'"))
        connection.execute(text("""
            UPDATE jobs SET country = 'India'
            WHERE country IS NULL AND LOWER(COALESCE(location, '')) ~ '\\m(bangalore|bengaluru|hyderabad|mumbai|delhi|gurgaon|gurugram|noida|pune|chennai|kolkata|ahmedabad|jaipur|kochi|indore|thiruvananthapuram)\\M'
        """))
        connection.execute(text("UPDATE jobs SET is_remote = TRUE WHERE LOWER(COALESCE(location, '')) LIKE '%remote%'"))
        connection.execute(text("UPDATE jobs SET role_type = 'ai' WHERE LOWER(COALESCE(title, '')) LIKE '%forward deployed%'"))
        connection.execute(text("UPDATE jobs SET role_type = 'sde' WHERE role_type IN ('full_stack', 'frontend', 'backend', 'web_engineer')"))
    db = SessionLocal()
    try:
        verification_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
        purge_stale_jobs(db, verification_cutoff)
        for seed_data in COMPANY_SEEDS:
            seed = db.scalar(select(CompanySeed).where(CompanySeed.company_name == seed_data["company_name"]))
            if seed:
                if not seed.website_url and seed_data["website_url"]:
                    seed.website_url = seed_data["website_url"]
                if not seed.careers_url and seed_data["careers_url"]:
                    seed.careers_url = seed_data["careers_url"]
                continue
            db.add(CompanySeed(
                **seed_data,
                status="queued" if seed_data["website_url"] else "needs_official_url",
            ))
        db.commit()
        for job in db.scalars(select(Job)).all():
            role_type = classify_role(job.title)
            if role_type is None:
                db.delete(job)
            else:
                job.role_type = role_type
        db.commit()
    finally:
        db.close()
    celery_app.send_task("app.worker.discover_company_seeds")
    celery_app.send_task("app.worker.discover_jobs")
    celery_app.send_task("app.worker.expire_stale_jobs")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/companies/seeds", response_model=list[CompanySeedOut])
def company_seeds(db: Session = Depends(get_db)) -> list[CompanySeedOut]:
    return db.scalars(select(CompanySeed).order_by(CompanySeed.company_name)).all()


@app.get("/api/jobs/alerts", response_model=JobAlertsOut)
def job_alerts(
    role_type: Literal["sde", "ai"] = Query(default="sde"),
    remote_only: bool = Query(default=True),
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> JobAlertsOut:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    filters = [Job.first_seen_at >= cutoff, Job.role_type == RoleType(role_type)]
    if remote_only:
        filters.append(Job.is_remote.is_(True))
    items = db.scalars(select(Job).where(*filters).order_by(Job.first_seen_at.desc()).limit(50)).all()
    return JobAlertsOut(
        items=[JobOut.model_validate(item) for item in items],
        total_new=len(items),
        last_checked_at=datetime.now(timezone.utc),
    )


@app.get("/api/jobs", response_model=JobPageOut)
def jobs(
    role_type: Literal["sde", "ai"] = Query(default="sde"),
    remote_only: bool = Query(default=True),
    skills: str | None = Query(default=None),
    location_eligibility: str | None = Query(default=None),
    internship_dates: str | None = Query(default=None),
    sort_by: Literal["priority", "fit", "freshness"] = Query(default="priority"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    filters = [Job.last_checked_at >= cutoff, Job.role_type == RoleType(role_type)]

    if remote_only:
        filters.append(Job.is_remote.is_(True))

    if location_eligibility:
        norm_loc = location_eligibility.lower()
        if norm_loc in ("remote", "any_remote"):
            filters.append(Job.is_remote.is_(True))
        elif norm_loc in ("india", "india_tech"):
            filters.append(or_(Job.country == "India", Job.is_remote.is_(True)))

    skills_list = [s.strip().lower() for s in (skills or "").split(",") if s.strip()]

    total = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)

    startup_source_urls = [
        canonical_url(board.careers_url) if board.platform == "schema" else _board_url(board.platform, board.slug)
        for board in db.scalars(select(StartupBoard)).all()
    ]
    startup_priority = case((Job.source_url.in_(startup_source_urls), 0), else_=1)
    remote_priority = case((Job.is_remote.is_(True), 0), else_=1)
    country_priority = case((Job.country == "India", 0), else_=1)

    order_clauses = [remote_priority, startup_priority, country_priority, Job.first_seen_at.desc()]
    if sort_by == "freshness":
        order_clauses = [Job.first_seen_at.desc(), remote_priority, startup_priority]

    query = select(Job).where(*filters).order_by(*order_clauses)
    
    # If fit ranking is requested, pull results and sort by fit score
    should_rank_fit = sort_by == "fit" or bool(skills_list)
    if should_rank_fit:
        all_matches = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
        scored_items: list[JobOut] = []
        for job in all_matches:
            fit_score, matched = _compute_fit(job, skills_list, location_eligibility, internship_dates)
            out = JobOut.model_validate(job)
            out.fit_score = fit_score
            out.matched_skills = matched
            scored_items.append(out)
        scored_items.sort(key=lambda x: (x.fit_score or 0, x.first_seen_at), reverse=True)
        return JobPageOut(
            items=scored_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    out_items: list[JobOut] = []
    for job in items:
        fit_score, matched = _compute_fit(job, skills_list, location_eligibility, internship_dates)
        out = JobOut.model_validate(job)
        out.fit_score = fit_score
        out.matched_skills = matched
        out_items.append(out)

    return JobPageOut(
        items=out_items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@app.get("/api/jobs/summary", response_model=SummaryOut)
def summary(remote_only: bool = Query(default=True), db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    filters = [Job.last_checked_at >= cutoff]
    if remote_only:
        filters.append(Job.is_remote.is_(True))
    rows = db.execute(select(Job.role_type, func.count(Job.id)).where(*filters).group_by(Job.role_type)).all()
    counts = {RoleType.sde.value: 0, RoleType.ai.value: 0}
    counts.update({role.value: count for role, count in rows})
    total_remote = db.scalar(select(func.count(Job.id)).where(Job.last_checked_at >= cutoff, Job.is_remote.is_(True))) or 0
    total_active = db.scalar(select(func.count(Job.id)).where(Job.last_checked_at >= cutoff)) or 0
    return SummaryOut(
        sde=counts.get(RoleType.sde.value, 0),
        ai=counts.get(RoleType.ai.value, 0),
        total_remote=total_remote,
        total_active=total_active,
    )
