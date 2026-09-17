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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from daily_win_api.db.base import Base
from daily_win_api.db.constraints import (
    child_household_foreign_key,
    daily_win_child_household_foreign_key,
    household_child_index,
    id_child_household_unique,
)
from daily_win_api.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class AiRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        child_household_foreign_key("fk_ai_runs_child_household"),
        household_child_index("ix_ai_runs_household_child"),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    output_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DailyWin(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "daily_wins"
    __table_args__ = (
        child_household_foreign_key("fk_daily_wins_child_household"),
        household_child_index("ix_daily_wins_household_child"),
        id_child_household_unique("uq_daily_wins_id_child_household"),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    primary_skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ai_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    content_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class DailyWinFeedback(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "daily_win_feedback"
    __table_args__ = (
        child_household_foreign_key("fk_daily_win_feedback_child_household"),
        daily_win_child_household_foreign_key(
            "fk_daily_win_feedback_win_child_household"
        ),
        id_child_household_unique("uq_daily_win_feedback_id_child_household"),
        UniqueConstraint("daily_win_id", name="uq_daily_win_feedback_daily_win_id"),
        household_child_index("ix_daily_win_feedback_household_child"),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    daily_win_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    engagement: Mapped[str] = mapped_column(String(32), nullable=False)
    completion: Mapped[str] = mapped_column(String(32), nullable=False)
    setback_response: Mapped[str] = mapped_column(String(32), nullable=False)
    what_helped: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
