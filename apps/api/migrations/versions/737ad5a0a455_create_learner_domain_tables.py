"""create learner domain tables

Revision ID: 737ad5a0a455
Revises: 
Create Date: 2026-09-17 15:52:55.836851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '737ad5a0a455'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('households',
    sa.Column('display_name', sa.String(length=120), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('skills',
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('domain', sa.String(length=32), nullable=False),
    sa.Column('display_name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('state_mode', sa.String(length=32), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_skills_domain'), 'skills', ['domain'], unique=False)
    op.create_table('children',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('nickname', sa.String(length=80), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'household_id', name='uq_children_id_household_id')
    )
    op.create_index(op.f('ix_children_household_id'), 'children', ['household_id'], unique=False)
    op.create_table('child_baselines',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('age_years', sa.Integer(), nullable=False),
    sa.Column('grade', sa.String(length=32), nullable=False),
    sa.Column('interests', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('current_difficulties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('motivators', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('response_to_difficulty', sa.Text(), nullable=True),
    sa.Column('preferred_activity_minutes', sa.Integer(), nullable=False),
    sa.Column('schema_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id', 'household_id'], ['children.id', 'children.household_id'], name='fk_child_baselines_child_household', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_child_baselines_household_child', 'child_baselines', ['household_id', 'child_id'], unique=False)
    op.create_table('child_goals',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('skill_id', sa.Uuid(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id', 'household_id'], ['children.id', 'children.household_id'], name='fk_child_goals_child_household', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_child_goals_household_child', 'child_goals', ['household_id', 'child_id'], unique=False)
    op.create_index(op.f('ix_child_goals_skill_id'), 'child_goals', ['skill_id'], unique=False)
    op.create_index('uq_child_goals_active_skill', 'child_goals', ['child_id', 'skill_id'], unique=True, postgresql_where=sa.text('active IS TRUE'))
    op.create_table('learner_skill_state',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('skill_id', sa.Uuid(), nullable=False),
    sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('evidence_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('algorithm_version', sa.String(length=32), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id', 'household_id'], ['children.id', 'children.household_id'], name='fk_learner_skill_state_child_household', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('household_id', 'child_id', 'skill_id', name='uq_learner_skill_state_child_skill')
    )
    op.create_index('ix_learner_skill_state_household_child', 'learner_skill_state', ['household_id', 'child_id'], unique=False)
    op.create_index(op.f('ix_learner_skill_state_skill_id'), 'learner_skill_state', ['skill_id'], unique=False)
    op.create_table('learning_events',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('skill_id', sa.Uuid(), nullable=True),
    sa.Column('evidence_kind', sa.String(length=32), nullable=False),
    sa.Column('source', sa.String(length=32), nullable=False),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('schema_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('supersedes_event_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id', 'household_id'], ['children.id', 'children.household_id'], name='fk_learning_events_child_household', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['supersedes_event_id'], ['learning_events.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_events_evidence_kind'), 'learning_events', ['evidence_kind'], unique=False)
    op.create_index('ix_learning_events_household_child', 'learning_events', ['household_id', 'child_id'], unique=False)
    op.create_index('ix_learning_events_occurred_at', 'learning_events', ['household_id', 'child_id', 'occurred_at'], unique=False)
    op.create_index(op.f('ix_learning_events_skill_id'), 'learning_events', ['skill_id'], unique=False)
    op.create_index(op.f('ix_learning_events_supersedes_event_id'), 'learning_events', ['supersedes_event_id'], unique=False)
    op.create_table(
        'learner_skill_state_evidence',
        sa.Column('learner_skill_state_id', sa.Uuid(), nullable=False),
        sa.Column('learning_event_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['learner_skill_state_id'], ['learner_skill_state.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['learning_event_id'], ['learning_events.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('learner_skill_state_id', 'learning_event_id')
    )
    op.create_index(
        op.f('ix_learner_skill_state_evidence_learning_event_id'),
        'learner_skill_state_evidence',
        ['learning_event_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_learner_skill_state_evidence_learning_event_id'),
        table_name='learner_skill_state_evidence',
    )
    op.drop_table('learner_skill_state_evidence')
    op.drop_index(op.f('ix_learning_events_supersedes_event_id'), table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_skill_id'), table_name='learning_events')
    op.drop_index('ix_learning_events_occurred_at', table_name='learning_events')
    op.drop_index('ix_learning_events_household_child', table_name='learning_events')
    op.drop_index(op.f('ix_learning_events_evidence_kind'), table_name='learning_events')
    op.drop_table('learning_events')
    op.drop_index(op.f('ix_learner_skill_state_skill_id'), table_name='learner_skill_state')
    op.drop_index('ix_learner_skill_state_household_child', table_name='learner_skill_state')
    op.drop_table('learner_skill_state')
    op.drop_index('uq_child_goals_active_skill', table_name='child_goals', postgresql_where=sa.text('active IS TRUE'))
    op.drop_index(op.f('ix_child_goals_skill_id'), table_name='child_goals')
    op.drop_index('ix_child_goals_household_child', table_name='child_goals')
    op.drop_table('child_goals')
    op.drop_index('ix_child_baselines_household_child', table_name='child_baselines')
    op.drop_table('child_baselines')
    op.drop_index(op.f('ix_children_household_id'), table_name='children')
    op.drop_table('children')
    op.drop_index(op.f('ix_skills_domain'), table_name='skills')
    op.drop_table('skills')
    op.drop_table('households')
