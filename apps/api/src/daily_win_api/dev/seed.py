from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import (
    DEMO_CHILD_ID,
    DEMO_CHILD_NICKNAME,
    DEMO_HOUSEHOLD_ID,
    demo_baseline_id,
    demo_goal_id,
    skill_id_for_code,
)
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.children.schemas import ChildBaselineCreate
from daily_win_api.domains.households.models import Household
from daily_win_api.domains.learning.models import ChildGoal, Skill
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS

DEMO_HOUSEHOLD_NAME = "Demo Household"
HAYES_GOAL_CODES = (
    "growth.persistence",
    "writing.organization",
    "growth.independence",
)


def seed_development_data(session: Session) -> None:
    """Idempotent development seed. Not production data and not authorization."""
    _seed_skills(session)
    session.flush()
    _seed_demo_household(session)
    session.flush()
    _seed_demo_child(session)
    session.flush()
    _seed_hayes_baseline(session)
    _seed_hayes_goals(session)
    session.flush()


def _seed_skills(session: Session) -> None:
    existing = {skill.code: skill for skill in session.scalars(select(Skill))}
    for definition in SKILL_DEFINITIONS:
        skill = existing.get(definition["code"])
        if skill is None:
            skill = Skill(id=skill_id_for_code(definition["code"]))
            session.add(skill)
        skill.code = definition["code"]
        skill.domain = definition["domain"]
        skill.display_name = definition["display_name"]
        skill.description = definition["description"]
        skill.state_mode = definition["state_mode"]
        skill.active = True


def _seed_demo_household(session: Session) -> None:
    household = session.get(Household, DEMO_HOUSEHOLD_ID)
    if household is None:
        household = Household(id=DEMO_HOUSEHOLD_ID)
        session.add(household)
    household.display_name = DEMO_HOUSEHOLD_NAME


def _seed_demo_child(session: Session) -> None:
    child = session.get(Child, DEMO_CHILD_ID)
    if child is None:
        child = Child(id=DEMO_CHILD_ID, household_id=DEMO_HOUSEHOLD_ID)
        session.add(child)
    child.household_id = DEMO_HOUSEHOLD_ID
    child.nickname = DEMO_CHILD_NICKNAME


def _seed_hayes_baseline(session: Session) -> None:
    snapshot = ChildBaselineCreate(
        age_years=7,
        grade="1",
        interests=["building things", "soccer", "Minecraft"],
        strengths=["math", "reading"],
        current_difficulties=[
            "writing",
            "persistence after an initial failure",
            "independent problem solving",
        ],
        motivators=["competition", "short challenges", "doing activities with Dad"],
        response_to_difficulty="becomes frustrated after the first failure",
        preferred_activity_minutes=20,
        schema_version=1,
    )
    baseline = session.get(ChildBaseline, demo_baseline_id())
    if baseline is None:
        baseline = ChildBaseline(
            id=demo_baseline_id(),
            household_id=DEMO_HOUSEHOLD_ID,
            child_id=DEMO_CHILD_ID,
            recorded_at=datetime.now(UTC),
        )
        session.add(baseline)
    baseline.household_id = DEMO_HOUSEHOLD_ID
    baseline.child_id = DEMO_CHILD_ID
    baseline.age_years = snapshot.age_years
    baseline.grade = snapshot.grade
    baseline.interests = snapshot.interests
    baseline.strengths = snapshot.strengths
    baseline.current_difficulties = snapshot.current_difficulties
    baseline.motivators = snapshot.motivators
    baseline.response_to_difficulty = snapshot.response_to_difficulty
    baseline.preferred_activity_minutes = snapshot.preferred_activity_minutes
    baseline.schema_version = snapshot.schema_version


def _seed_hayes_goals(session: Session) -> None:
    for priority, code in enumerate(HAYES_GOAL_CODES, start=1):
        goal_id = demo_goal_id(code)
        goal = session.get(ChildGoal, goal_id)
        if goal is None:
            goal = ChildGoal(id=goal_id)
            session.add(goal)
        goal.household_id = DEMO_HOUSEHOLD_ID
        goal.child_id = DEMO_CHILD_ID
        goal.skill_id = skill_id_for_code(code)
        goal.priority = priority
        goal.active = True
