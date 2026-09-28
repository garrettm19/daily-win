from sqlalchemy import func, select

from daily_win_api.core.demo import (
    DEMO_CHILD_ID,
    DEMO_CHILD_NICKNAME,
    DEMO_HOUSEHOLD_ID,
)
from daily_win_api.dev.presets import HAYES_PROFILE
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.dev.seed import HAYES_GOAL_CODES, seed_development_data
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.households.models import Household
from daily_win_api.domains.learning.models import ChildGoal, LearnerSkillState, Skill
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS


def test_demo_seed_is_idempotent(db_session) -> None:
    seed_development_data(db_session)
    seed_development_data(db_session)
    reset_demo_derived_data(db_session)
    seed_development_data(db_session)

    skill_count = db_session.scalar(select(func.count()).select_from(Skill))
    assert skill_count == len(SKILL_DEFINITIONS)

    household_count = db_session.scalar(
        select(func.count())
        .select_from(Household)
        .where(Household.id == DEMO_HOUSEHOLD_ID)
    )
    assert household_count == 1

    child_count = db_session.scalar(
        select(func.count()).select_from(Child).where(Child.id == DEMO_CHILD_ID)
    )
    assert child_count == 1

    child = db_session.get(Child, DEMO_CHILD_ID)
    assert child is not None
    assert child.household_id == DEMO_HOUSEHOLD_ID
    assert child.nickname == DEMO_CHILD_NICKNAME

    latest = db_session.scalars(
        select(ChildBaseline)
        .where(ChildBaseline.child_id == DEMO_CHILD_ID)
        .order_by(ChildBaseline.recorded_at.desc())
        .limit(1)
    ).first()
    assert latest is not None
    assert latest.age_years == HAYES_PROFILE.age_years
    assert latest.grade == HAYES_PROFILE.grade
    assert list(latest.interests) == list(HAYES_PROFILE.interests)
    assert "caregiver" in " ".join(latest.motivators)
    assert "Dad" not in " ".join(latest.motivators)

    goals = db_session.scalars(
        select(ChildGoal)
        .where(ChildGoal.child_id == DEMO_CHILD_ID, ChildGoal.active.is_(True))
        .order_by(ChildGoal.priority)
    ).all()
    assert [goal.priority for goal in goals] == [1, 2, 3]
    assert len(goals) == len(HAYES_GOAL_CODES)

    derived_state_count = db_session.scalar(
        select(func.count())
        .select_from(LearnerSkillState)
        .where(LearnerSkillState.child_id == DEMO_CHILD_ID)
    )
    assert derived_state_count == 0
