from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, case, func, inspect, or_, select, text
from sqlalchemy.orm import Session
from app.config import get_settings
from app.classifier import classify_role
from app.crawler import _board_url, canonical_url, get_ats_name
from app.database import Base, SessionLocal, engine, get_db
from app.models import CompanySeed, Job, RoleType, StartupBoard
from app.schemas import CompanySeedOut, JobOut, JobPageOut, SummaryOut
from app.worker import _upsert_discovered_jobs, celery_app, purge_stale_jobs
from app.company_seeds import COMPANY_SEEDS
from app.indian_jobs_data import INDIAN_COMPANIES_LIST, INDIAN_INTERNSHIP_SEEDS, STARTUP_COMPANIES_LIST

settings = get_settings()
app = FastAPI(title="InternRoleFinder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

INDIAN_CITIES_PATTERN = r"\m(india|bangalore|bengaluru|hyderabad|mumbai|delhi|gurgaon|gurugram|noida|pune|chennai|kolkata|ahmedabad|jaipur|kochi|indore|chandigarh|coimbatore|trivandrum|thiruvananthapuram)\M"
INDIAN_COMPANIES_LOWER = [c.lower() for c in INDIAN_COMPANIES_LIST]
STARTUP_COMPANIES_LOWER = [c.lower() for c in STARTUP_COMPANIES_LIST]


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        for role_value in ("sde", "frontend", "backend", "full_stack"):
            with engine.begin() as connection:
                try:
                    connection.execute(text(f"ALTER TYPE role_type ADD VALUE IF NOT EXISTS '{role_value}'"))
                except Exception:
                    pass

    job_columns = {column["name"] for column in inspect(engine).get_columns("jobs")}
    with engine.begin() as connection:
        if "location" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN location VARCHAR(300)"))
        if "country" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN country VARCHAR(150)"))
        if "is_remote" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN is_remote BOOLEAN NOT NULL DEFAULT FALSE"))
        if "is_startup" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN is_startup BOOLEAN NOT NULL DEFAULT FALSE"))
        if "description" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN description TEXT"))
        if "posted_at" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN posted_at TIMESTAMP WITH TIME ZONE"))

        connection.execute(text("UPDATE jobs SET role_type = 'sde' WHERE role_type::text IN ('ai', 'other', 'web_engineer')"))
        # Fix inadvertent Indianapolis match and correctly set country to India for Indian hubs
        connection.execute(text("UPDATE jobs SET country = NULL WHERE LOWER(COALESCE(location, '')) LIKE '%indianapolis%' AND country = 'India'"))
        connection.execute(text("""
            UPDATE jobs SET country = 'India'
            WHERE (country IS NULL OR country != 'India')
            AND LOWER(COALESCE(location, '')) ~* '\\m(india|bangalore|bengaluru|hyderabad|mumbai|delhi|gurgaon|gurugram|noida|pune|chennai|kolkata|ahmedabad|jaipur|kochi|indore|chandigarh|coimbatore|trivandrum|thiruvananthapuram)\\M'
            AND LOWER(COALESCE(location, '')) !~* 'indianapolis'
        """))
        connection.execute(text("UPDATE jobs SET is_remote = TRUE WHERE LOWER(COALESCE(location, '')) LIKE '%remote%'"))

        # Tag startups based on modern ATS domains or curated startup lists
        connection.execute(text("""
            UPDATE jobs SET is_startup = TRUE
            WHERE is_startup = FALSE
            AND (
                LOWER(COALESCE(company, '')) = ANY(:startup_companies)
                OR LOWER(COALESCE(apply_url, '')) ~* '(ashbyhq\\.com|jobs\\.lever\\.co|boards\\.greenhouse\\.io|job-boards\\.greenhouse\\.io|apply\\.workable\\.com|recruitee\\.com|keka\\.com|freshteam\\.com)'
            )
            AND LOWER(COALESCE(company, '')) !~* '(amazon|microsoft|google|meta|apple|ibm|oracle|intel|cisco|dell|hp|tcs|infosys|wipro|cognizant|accenture|capgemini|walmart|jpmorgan|goldman|siemens|bosch)'
        """), {"startup_companies": list(STARTUP_COMPANIES_LOWER)})

    db = SessionLocal()
    try:
        verification_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
        purge_stale_jobs(db, verification_cutoff)

        # Seed Indian tech company startup boards & seeds
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

        # Seed verified Indian & high-growth startup company internship roles
        from app.crawler import ExtractedJob
        indian_jobs_to_upsert = [
            ExtractedJob(
                title=item["title"],
                company=item["company"],
                location=item["location"],
                country=item.get("country", "India"),
                is_remote=item.get("is_remote", False),
                is_startup=item.get("is_startup", True),
                role_type=item["role_type"],
                apply_url=item["apply_url"],
                source_url=item["source_url"],
                description=item.get("description"),
            )
            for item in INDIAN_INTERNSHIP_SEEDS
        ]
        _upsert_discovered_jobs(db, indian_jobs_to_upsert)
        db.commit()

        # Ensure all existing jobs conform to valid role categories
        for job in db.scalars(select(Job)).all():
            classified = classify_role(job.title)
            if classified is None:
                db.delete(job)
            else:
                job.role_type = classified
        db.commit()

        # Ensure database maintains at least 200 active roles
        active_count = db.scalar(select(func.count(Job.id)).where(Job.last_checked_at >= verification_cutoff)) or 0
        if active_count < 200:
            import asyncio
            from app.crawler import discover_jobs_from_verified_listings
            try:
                verified_jobs = asyncio.run(discover_jobs_from_verified_listings(limit=500))
                _upsert_discovered_jobs(db, verified_jobs)
                db.commit()
            except Exception:
                pass
    finally:
        db.close()

    try:
        celery_app.send_task("app.worker.discover_company_seeds")
        celery_app.send_task("app.worker.discover_jobs")
        celery_app.send_task("app.worker.expire_stale_jobs")
    except Exception:
        pass


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/companies/seeds", response_model=list[CompanySeedOut])
def company_seeds(db: Session = Depends(get_db)) -> list[CompanySeedOut]:
    return db.scalars(select(CompanySeed).order_by(CompanySeed.company_name)).all()


@app.get("/api/jobs", response_model=JobPageOut)
def jobs(
    role_type: Literal["all", "sde", "frontend", "backend", "full_stack"] | None = None,
    remote_only: bool = False,
    startups_only: bool = False,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    filters = [Job.last_checked_at >= cutoff]

    if role_type and role_type != "all":
        filters.append(Job.role_type == RoleType(role_type))

    if isinstance(remote_only, bool) and remote_only:
        filters.append(Job.is_remote.is_(True))

    if isinstance(startups_only, bool) and startups_only:
        filters.append(Job.is_startup.is_(True))

    if isinstance(search, str) and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Job.title.ilike(term),
                Job.company.ilike(term),
                Job.location.ilike(term),
                Job.description.ilike(term),
            )
        )

    total = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)

    startup_source_urls = [
        canonical_url(board.careers_url) if board.platform == "schema" else _board_url(board.platform, board.slug)
        for board in db.scalars(select(StartupBoard)).all()
    ]

    # TOP PRIORITY: Indian companies and India-located roles appear first (0 before 1)
    india_priority = case(
        (
            or_(
                Job.country == "India",
                func.lower(Job.company).in_(INDIAN_COMPANIES_LOWER),
                and_(
                    func.lower(Job.location).op("~*")(INDIAN_CITIES_PATTERN),
                    func.lower(Job.location).not_ilike("%indianapolis%"),
                ),
            ),
            0,
        ),
        else_=1,
    )
    remote_priority = case((Job.is_remote.is_(True), 0), else_=1)
    startup_priority = case(
        (
            or_(
                Job.is_startup.is_(True),
                Job.source_url.in_(startup_source_urls),
            ),
            0,
        ),
        else_=1,
    )

    order_clauses = [india_priority, remote_priority, startup_priority, Job.first_seen_at.desc()]
    query = select(Job).where(*filters).order_by(*order_clauses)

    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    out_items = [
        JobOut(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            country=job.country,
            is_remote=job.is_remote,
            is_startup=job.is_startup,
            ats_type=get_ats_name(job.apply_url),
            role_type=job.role_type,
            description=job.description,
            posted_at=job.posted_at,
            apply_url=job.apply_url,
            first_seen_at=job.first_seen_at,
            last_checked_at=job.last_checked_at,
        )
        for job in items
    ]

    return JobPageOut(
        items=out_items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@app.get("/api/jobs/summary", response_model=SummaryOut)
def summary(
    remote_only: bool = False,
    startups_only: bool = False,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    filters = [Job.last_checked_at >= cutoff]
    if isinstance(remote_only, bool) and remote_only:
        filters.append(Job.is_remote.is_(True))
    if isinstance(startups_only, bool) and startups_only:
        filters.append(Job.is_startup.is_(True))

    rows = db.execute(select(Job.role_type, func.count(Job.id)).where(*filters).group_by(Job.role_type)).all()
    counts = {r.value: 0 for r in RoleType}
    counts.update({role.value: count for role, count in rows})

    total_active = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
    total_remote = db.scalar(select(func.count(Job.id)).where(Job.last_checked_at >= cutoff, Job.is_remote.is_(True))) or 0
    total_startups = db.scalar(select(func.count(Job.id)).where(Job.last_checked_at >= cutoff, Job.is_startup.is_(True))) or 0

    return SummaryOut(
        all=total_active,
        sde=counts.get(RoleType.sde.value, 0),
        frontend=counts.get(RoleType.frontend.value, 0),
        backend=counts.get(RoleType.backend.value, 0),
        full_stack=counts.get(RoleType.full_stack.value, 0),
        total_remote=total_remote,
        total_startups=total_startups,
    )

