from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, case, func, inspect, select, text
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import Base, engine, get_db
from app.models import Job, RoleType
from app.schemas import JobOut, JobPageOut, SummaryOut
from app.worker import celery_app

settings = get_settings()
app = FastAPI(title="InternRoleFinder API")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    job_columns = {column["name"] for column in inspect(engine).get_columns("jobs")}
    with engine.begin() as connection:
        if "location" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN location VARCHAR(300)"))
        if "country" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN country VARCHAR(150)"))
        if "is_remote" not in job_columns:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN is_remote BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("UPDATE jobs SET country = 'India' WHERE country IS NULL AND LOWER(COALESCE(location, '')) LIKE '%india%'"))
        connection.execute(text("UPDATE jobs SET is_remote = TRUE WHERE LOWER(COALESCE(location, '')) LIKE '%remote%'"))
        connection.execute(text("UPDATE jobs SET role_type = 'sde' WHERE role_type IN ('full_stack', 'frontend', 'backend', 'web_engineer')"))
    if engine.dialect.name == "postgresql":
        for role_value in ("ai", "other"):
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TYPE role_type ADD VALUE IF NOT EXISTS '{role_value}'"))
    # Start a discovery pass after each application startup. Redis keeps the
    # task until the worker is ready, avoiding an empty dashboard after a restart.
    if settings.gemini_api_key and settings.gemini_api_key.get_secret_value().strip():
        celery_app.send_task("app.worker.discover_indian_startups")
    celery_app.send_task("app.worker.discover_jobs")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/jobs", response_model=JobPageOut)
def jobs(
    role_type: RoleType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    filters = [Job.last_checked_at >= cutoff]
    if role_type:
        filters.append(Job.role_type == role_type)
    total = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    sort_priority = case(
        (and_(Job.country == "India", Job.is_remote.is_(True)), 0),
        (Job.country == "India", 1),
        (Job.is_remote.is_(True), 2),
        else_=3,
    )
    query = (
        select(Job)
        .where(*filters)
        .order_by(sort_priority, Job.first_seen_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return JobPageOut(
        items=db.scalars(query).all(),
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@app.get("/api/jobs/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.verification_max_age_hours)
    rows = db.execute(select(Job.role_type, func.count(Job.id)).where(Job.last_checked_at >= cutoff).group_by(Job.role_type)).all()
    counts = {role.value: 0 for role in RoleType}
    counts.update({role.value: count for role, count in rows})
    return counts
