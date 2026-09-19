from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from daily_win_api.db.base import Base
from daily_win_api.db.constraints import child_household_foreign_key
from daily_win_api.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class DemoSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Development-only mapping from a hashed session secret to a synthetic tenant.

    This is not authentication. The raw session secret is never stored.
    """

    __tablename__ = "demo_sessions"
    __table_args__ = (
        child_household_foreign_key("fk_demo_sessions_child_household"),
        UniqueConstraint("household_id", name="uq_demo_sessions_household_id"),
        UniqueConstraint("child_id", name="uq_demo_sessions_child_id"),
    )

    session_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    household_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    profile_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
