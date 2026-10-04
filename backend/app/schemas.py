from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl
from app.types import RoleType


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str | None
    location: str | None
    country: str | None
    is_remote: bool
    is_startup: bool = False
    ats_type: str | None = None
    career_url: str | None = None
    role_type: RoleType
    description: str | None = None
    posted_at: datetime | None = None
    apply_url: str
    source: str | None = None
    source_job_id: str | None = None
    original_url: str | None = None
    job_url: str | None = None
    final_url: str | None = None
    status: str = "active"
    last_verified_at: datetime | None = None
    first_seen_at: datetime
    last_checked_at: datetime


class SummaryOut(BaseModel):
    all: int = 0
    sde: int = 0
    frontend: int = 0
    backend: int = 0
    full_stack: int = 0
    total_remote: int = 0
    total_startups: int = 0


class JobPageOut(BaseModel):
    items: list[JobOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class CompanySeedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_name: str
    website_url: HttpUrl | None
    careers_url: HttpUrl | None
    enabled: bool
    status: str
    last_checked_at: datetime | None
    last_error: str | None
