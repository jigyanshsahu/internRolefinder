from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from app.types import RoleType


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str | None
    location: str | None
    country: str | None
    is_remote: bool
    role_type: RoleType
    description: str | None = None
    posted_at: datetime | None = None
    apply_url: HttpUrl
    first_seen_at: datetime
    last_checked_at: datetime
    fit_score: int | None = None
    matched_skills: list[str] = Field(default_factory=list)


class SummaryOut(BaseModel):
    sde: int = 0
    ai: int = 0
    total_remote: int = 0
    total_active: int = 0


class JobPageOut(BaseModel):
    items: list[JobOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class JobAlertsOut(BaseModel):
    items: list[JobOut]
    total_new: int
    last_checked_at: datetime


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
