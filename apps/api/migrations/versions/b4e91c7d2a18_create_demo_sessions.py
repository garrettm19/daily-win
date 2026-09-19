"""create demo_sessions table

Revision ID: b4e91c7d2a18
Revises: e8f3c1b92a04
Create Date: 2026-09-18 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e91c7d2a18"
down_revision: Union[str, Sequence[str], None] = "e8f3c1b92a04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_sessions",
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_id", "household_id"],
            ["children.id", "children.household_id"],
            name="fk_demo_sessions_child_household",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_hash"),
        sa.UniqueConstraint("household_id", name="uq_demo_sessions_household_id"),
        sa.UniqueConstraint("child_id", name="uq_demo_sessions_child_id"),
    )


def downgrade() -> None:
    op.drop_table("demo_sessions")
