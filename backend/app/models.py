import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RoleType(str, enum.Enum):
    sde = "sde"
    ai = "ai"
    other = "other"


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    country: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    role_type: Mapped[RoleType] = mapped_column(Enum(RoleType, name="role_type"), index=True)
    apply_url: Mapped[str] = mapped_column(Text, unique=True)
    source_url: Mapped[str] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StartupBoard(Base):
    __tablename__ = "startup_boards"
    __table_args__ = (UniqueConstraint("platform", "slug", name="uq_startup_boards_platform_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(300))
    platform: Mapped[str] = mapped_column(String(40))
    slug: Mapped[str] = mapped_column(String(300))
    careers_url: Mapped[str] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
