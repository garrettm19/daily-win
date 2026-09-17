"""create daily win feedback and evidence lineage

Revision ID: e8f3c1b92a04
Revises: dac0a25a697d
Create Date: 2026-09-17 17:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f3c1b92a04"
down_revision: Union[str, Sequence[str], None] = "dac0a25a697d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_daily_wins_id_child_household",
        "daily_wins",
        ["id", "child_id", "household_id"],
    )
    op.create_table(
        "daily_win_feedback",
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("daily_win_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("engagement", sa.String(length=32), nullable=False),
        sa.Column("completion", sa.String(length=32), nullable=False),
        sa.Column("setback_response", sa.String(length=32), nullable=False),
        sa.Column("what_helped", sa.Text(), nullable=True),
        sa.Column("additional_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["child_id", "household_id"],
            ["children.id", "children.household_id"],
            name="fk_daily_win_feedback_child_household",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["daily_win_id", "child_id", "household_id"],
            ["daily_wins.id", "daily_wins.child_id", "daily_wins.household_id"],
            name="fk_daily_win_feedback_win_child_household",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "child_id",
            "household_id",
            name="uq_daily_win_feedback_id_child_household",
        ),
        sa.UniqueConstraint("daily_win_id", name="uq_daily_win_feedback_daily_win_id"),
    )
    op.create_index(
        "ix_daily_win_feedback_household_child",
        "daily_win_feedback",
        ["household_id", "child_id"],
        unique=False,
    )
    op.add_column(
        "learning_events", sa.Column("daily_win_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "learning_events",
        sa.Column("daily_win_feedback_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_learning_events_daily_win_id"),
        "learning_events",
        ["daily_win_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_events_daily_win_feedback_id"),
        "learning_events",
        ["daily_win_feedback_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_learning_events_daily_win_id",
        "learning_events",
        "daily_wins",
        ["daily_win_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_learning_events_daily_win_feedback_id",
        "learning_events",
        "daily_win_feedback",
        ["daily_win_feedback_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_learning_events_daily_win_feedback_id",
        "learning_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_learning_events_daily_win_id",
        "learning_events",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_learning_events_daily_win_feedback_id"),
        table_name="learning_events",
    )
    op.drop_index(
        op.f("ix_learning_events_daily_win_id"), table_name="learning_events"
    )
    op.drop_column("learning_events", "daily_win_feedback_id")
    op.drop_column("learning_events", "daily_win_id")
    op.drop_index(
        "ix_daily_win_feedback_household_child", table_name="daily_win_feedback"
    )
    op.drop_table("daily_win_feedback")
    op.drop_constraint(
        "uq_daily_wins_id_child_household", "daily_wins", type_="unique"
    )
