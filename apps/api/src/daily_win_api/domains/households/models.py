from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from daily_win_api.db.base import Base
from daily_win_api.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Household(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "households"

    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
