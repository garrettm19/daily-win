"""learner engine curriculum plans and decision runs

Revision ID: a1c3e5f70912
Revises: c7a14e8b3d90
Create Date: 2026-09-19 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1c3e5f70912"
down_revision: Union[str, Sequence[str], None] = "c7a14e8b3d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column(
            "skill_kind",
            sa.String(length=16),
            server_default=sa.text("'strand'"),
            nullable=False,
        ),
    )
    op.add_column("skills", sa.Column("strand", sa.String(length=64), nullable=True))
    op.add_column(
        "skills", sa.Column("parent_code", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "skills",
        sa.Column(
            "grade_band_min",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "grade_band_max",
            sa.Integer(),
            server_default=sa.text("9"),
            nullable=False,
        ),
    )
    op.add_column("skills", sa.Column("measurable_outcome", sa.Text(), nullable=True))
    op.add_column(
        "skills",
        sa.Column(
            "progression_position",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "taxonomy_version",
            sa.String(length=32),
            server_default=sa.text("'curriculum_v1'"),
            nullable=False,
        ),
    )
    op.create_index("ix_skills_parent_code", "skills", ["parent_code"], unique=False)

    op.create_table(
        "skill_prerequisites",
        sa.Column("skill_code", sa.String(length=64), nullable=False),
        sa.Column("prerequisite_code", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["skill_code"], ["skills.code"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_code"], ["skills.code"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("skill_code", "prerequisite_code"),
    )
    op.create_table(
        "skill_standard_refs",
        sa.Column("skill_code", sa.String(length=64), nullable=False),
        sa.Column("standard_code", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["skill_code"], ["skills.code"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "skill_code",
            "standard_code",
            "source",
            "version",
            name="uq_skill_standard_refs",
        ),
    )
    op.create_index(
        "ix_skill_standard_refs_skill_code",
        "skill_standard_refs",
        ["skill_code"],
        unique=False,
    )

    op.create_table(
        "instruction_plans",
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("primary_skill_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("instruction_mode", sa.String(length=32), nullable=False),
        sa.Column("scaffold_level", sa.String(length=32), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            name="fk_instruction_plans_child_household",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["primary_skill_id"], ["skills.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instruction_plans_household_child",
        "instruction_plans",
        ["household_id", "child_id"],
        unique=False,
    )
    op.create_index(
        "ix_instruction_plans_household_child_created",
        "instruction_plans",
        ["household_id", "child_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instruction_plans_primary_skill_id"),
        "instruction_plans",
        ["primary_skill_id"],
        unique=False,
    )

    op.add_column(
        "daily_wins",
        sa.Column("instruction_plan_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_daily_wins_instruction_plan_id"),
        "daily_wins",
        ["instruction_plan_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_daily_wins_instruction_plan_id",
        "daily_wins",
        "instruction_plans",
        ["instruction_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_daily_wins_household_child_created",
        "daily_wins",
        ["household_id", "child_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "daily_win_feedback",
        sa.Column("academic_result", sa.String(length=48), nullable=True),
    )
    op.add_column(
        "daily_win_feedback",
        sa.Column("correct_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "daily_win_feedback",
        sa.Column("attempted_count", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_learning_events_child_skill_occurred",
        "learning_events",
        ["household_id", "child_id", "skill_id", "occurred_at"],
        unique=False,
    )

    op.create_table(
        "decision_runs",
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("instruction_plan_id", sa.Uuid(), nullable=True),
        sa.Column("daily_win_id", sa.Uuid(), nullable=True),
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
            name="fk_decision_runs_child_household",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instruction_plan_id"],
            ["instruction_plans.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["daily_win_id"], ["daily_wins.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_runs_household_child",
        "decision_runs",
        ["household_id", "child_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_runs_household_child_created",
        "decision_runs",
        ["household_id", "child_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_decision_runs_instruction_plan_id"),
        "decision_runs",
        ["instruction_plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_decision_runs_daily_win_id"),
        "decision_runs",
        ["daily_win_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_decision_runs_daily_win_id"), table_name="decision_runs")
    op.drop_index(
        op.f("ix_decision_runs_instruction_plan_id"), table_name="decision_runs"
    )
    op.drop_index(
        "ix_decision_runs_household_child_created", table_name="decision_runs"
    )
    op.drop_index("ix_decision_runs_household_child", table_name="decision_runs")
    op.drop_table("decision_runs")

    op.drop_index(
        "ix_learning_events_child_skill_occurred", table_name="learning_events"
    )

    op.drop_column("daily_win_feedback", "attempted_count")
    op.drop_column("daily_win_feedback", "correct_count")
    op.drop_column("daily_win_feedback", "academic_result")

    op.drop_index(
        "ix_daily_wins_household_child_created", table_name="daily_wins"
    )
    op.drop_constraint(
        "fk_daily_wins_instruction_plan_id", "daily_wins", type_="foreignkey"
    )
    op.drop_index(op.f("ix_daily_wins_instruction_plan_id"), table_name="daily_wins")
    op.drop_column("daily_wins", "instruction_plan_id")

    op.drop_index(
        op.f("ix_instruction_plans_primary_skill_id"),
        table_name="instruction_plans",
    )
    op.drop_index(
        "ix_instruction_plans_household_child_created",
        table_name="instruction_plans",
    )
    op.drop_index(
        "ix_instruction_plans_household_child", table_name="instruction_plans"
    )
    op.drop_table("instruction_plans")

    op.drop_index(
        "ix_skill_standard_refs_skill_code", table_name="skill_standard_refs"
    )
    op.drop_table("skill_standard_refs")
    op.drop_table("skill_prerequisites")

    op.drop_index("ix_skills_parent_code", table_name="skills")
    op.drop_column("skills", "taxonomy_version")
    op.drop_column("skills", "progression_position")
    op.drop_column("skills", "measurable_outcome")
    op.drop_column("skills", "grade_band_max")
    op.drop_column("skills", "grade_band_min")
    op.drop_column("skills", "parent_code")
    op.drop_column("skills", "strand")
    op.drop_column("skills", "skill_kind")
