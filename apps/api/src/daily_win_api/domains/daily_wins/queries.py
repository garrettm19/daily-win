from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.feedback import feedback_exists_for_win
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_READY,
    DemoDailyWinRead,
)
from daily_win_api.domains.learning.models import Skill


def get_latest_demo_daily_win(session: Session) -> DemoDailyWinRead | None:
    child = get_demo_child(session)
    if child is None:
        return None
    daily_win = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc())
        .limit(1)
    ).first()
    if daily_win is None:
        return None
    skill = session.get(Skill, daily_win.primary_skill_id)
    if skill is None:
        return None
    return to_demo_daily_win_read(session, daily_win, skill, child.nickname)


def to_demo_daily_win_read(
    session: Session, daily_win: DailyWin, primary_skill: Skill, child_nickname: str
) -> DemoDailyWinRead:
    return DemoDailyWinRead(
        id=daily_win.id,
        child_nickname=child_nickname,
        title=daily_win.title,
        objective=daily_win.objective,
        duration_minutes=daily_win.duration_minutes,
        primary_skill_code=primary_skill.code,
        primary_skill_display_name=primary_skill.display_name,
        content=DailyWinDraft.model_validate(daily_win.content),
        has_feedback=feedback_exists_for_win(session, daily_win.id),
        created_at=daily_win.created_at,
    )
