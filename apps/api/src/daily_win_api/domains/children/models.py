from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from daily_win_api.db.base import Base
from daily_win_api.db.constraints import (
    child_household_foreign_key,
    household_child_index,
)
from daily_win_api.db.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Child(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "children"
    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_children_id_household_id"),
    )

    household_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)


class ChildBaseline(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "child_baselines"
    __table_args__ = (
        child_household_foreign_key("fk_child_baselines_child_household"),
        household_child_index("ix_child_baselines_household_child"),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(32), nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    current_difficulties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    motivators: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    response_to_difficulty: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_activity_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
