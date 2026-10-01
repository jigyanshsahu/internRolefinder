from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl
from app.models import RoleType


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    company: str | None
    location: str | None
    country: str | None
    is_remote: bool
    role_type: RoleType
    apply_url: HttpUrl
    first_seen_at: datetime
    last_checked_at: datetime


class SummaryOut(BaseModel):
    sde: int = 0
    ai: int = 0


class JobPageOut(BaseModel):
    items: list[JobOut]
    page: int
    page_size: int
    total: int
    total_pages: int
