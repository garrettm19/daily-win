"""allow unconfigured demo sessions

Revision ID: c7a14e8b3d90
Revises: b4e91c7d2a18
Create Date: 2026-09-18 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a14e8b3d90"
down_revision: Union[str, Sequence[str], None] = "b4e91c7d2a18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "demo_sessions",
        "child_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "demo_sessions",
        sa.Column("profile_source", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM demo_sessions WHERE child_id IS NULL"))
    op.drop_column("demo_sessions", "profile_source")
    op.alter_column(
        "demo_sessions",
        "child_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
