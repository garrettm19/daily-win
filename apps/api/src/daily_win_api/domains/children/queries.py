from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.children.models import ChildBaseline
from daily_win_api.domains.children.schemas import (
    DemoBaselineSummary,
    DemoChildProfileRead,
    DemoChildSummary,
    DemoGoalSummary,
)
from daily_win_api.domains.learning.models import ChildGoal, Skill


class DemoChildProfileUnavailableError(Exception):
    """The synthetic demo child or a baseline snapshot is missing."""


def load_demo_child_profile(session: Session) -> DemoChildProfileRead:
    """Compose the demo profile from PostgreSQL. Not authorization."""
    child = get_demo_child(session)
    if child is None:
        raise DemoChildProfileUnavailableError

    baseline = session.scalars(
        select(ChildBaseline)
        .where(
            ChildBaseline.child_id == child.id,
            ChildBaseline.household_id == child.household_id,
        )
        .order_by(ChildBaseline.recorded_at.desc())
        .limit(1)
    ).first()
    if baseline is None:
        raise DemoChildProfileUnavailableError

    goal_rows = session.execute(
        select(ChildGoal, Skill)
        .join(Skill, Skill.id == ChildGoal.skill_id)
        .where(
            ChildGoal.child_id == child.id,
            ChildGoal.household_id == child.household_id,
            ChildGoal.active.is_(True),
        )
        .order_by(ChildGoal.priority.asc())
    ).all()

    return DemoChildProfileRead(
        child=DemoChildSummary(id=child.id, nickname=child.nickname),
        baseline=DemoBaselineSummary(
            age_years=baseline.age_years,
            grade=baseline.grade,
            interests=list(baseline.interests),
            strengths=list(baseline.strengths),
            current_difficulties=list(baseline.current_difficulties),
            motivators=list(baseline.motivators),
            response_to_difficulty=baseline.response_to_difficulty,
            preferred_activity_minutes=baseline.preferred_activity_minutes,
            recorded_at=baseline.recorded_at,
        ),
        goals=[
            DemoGoalSummary(
                priority=goal.priority,
                skill_code=skill.code,
                display_name=skill.display_name,
                domain=skill.domain,
            )
            for goal, skill in goal_rows
        ],
    )
