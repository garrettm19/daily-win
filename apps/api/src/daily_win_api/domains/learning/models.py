from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
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


class Skill(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "skills"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class ChildGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "child_goals"
    __table_args__ = (
        child_household_foreign_key("fk_child_goals_child_household"),
        household_child_index("ix_child_goals_household_child"),
        Index(
            "uq_child_goals_active_skill",
            "child_id",
            "skill_id",
            unique=True,
            postgresql_where=text("active IS TRUE"),
        ),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class LearningEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        child_household_foreign_key("fk_learning_events_child_household"),
        household_child_index("ix_learning_events_household_child"),
        Index(
            "ix_learning_events_occurred_at",
            "household_id",
            "child_id",
            "occurred_at",
        ),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    supersedes_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    daily_win_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_wins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    daily_win_feedback_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_win_feedback.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class LearnerSkillState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learner_skill_state"
    __table_args__ = (
        child_household_foreign_key("fk_learner_skill_state_child_household"),
        household_child_index("ix_learner_skill_state_household_child"),
        UniqueConstraint(
            "household_id",
            "child_id",
            "skill_id",
            name="uq_learner_skill_state_child_skill",
        ),
    )

    household_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    child_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class LearnerSkillStateEvidence(CreatedAtMixin, Base):
    __tablename__ = "learner_skill_state_evidence"

    learner_skill_state_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_skill_state.id", ondelete="CASCADE"),
        primary_key=True,
    )
    learning_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_events.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
