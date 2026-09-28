"""Rebuild weekly summaries from canonical events. Demo-facing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.context import prepare_daily_win_generation
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_READY,
    ContextUnavailableError,
)
from daily_win_api.domains.learning.explanations import display_name
from daily_win_api.domains.learning.models import (
    InstructionPlanRecord,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.observations import (
    OBSERVATION_BONUS_ENGAGEMENT,
    OBSERVATION_EFFORT,
    OBSERVATION_NON_TARGET,
    OBSERVATION_NOTICE,
    OBSERVATION_SELF_CORRECTION,
    OBSERVATION_STRATEGY,
)
from daily_win_api.domains.learning.signals import EVENT_TYPE_SKILL_OBSERVATION
from daily_win_api.domains.learning.taxonomy import (
    is_academic_code,
    is_growth_or_life_code,
)
from daily_win_api.domains.learning.weekly import (
    NextWeekPreview,
    SessionEvidence,
    WeeklyLearningSummary,
    synthesize_week,
)


def load_weekly_summary(session: Session, child: Child) -> WeeklyLearningSummary:
    now = datetime.now(UTC)
    week_start = now - timedelta(days=7)
    rows = session.execute(
        select(DailyWin, DailyWinFeedback, Skill)
        .join(DailyWinFeedback, DailyWinFeedback.daily_win_id == DailyWin.id)
        .join(Skill, Skill.id == DailyWin.primary_skill_id)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
            DailyWinFeedback.submitted_at >= week_start,
        )
        .order_by(DailyWinFeedback.submitted_at.asc())
    ).all()
    sessions = tuple(
        _session_from_row(session, win, feedback, skill)
        for win, feedback, skill in rows
    )
    next_week = _next_week_preview(session, child)
    return synthesize_week(
        sessions,
        week_start=week_start,
        week_end=now,
        next_week=next_week,
    )


def _next_week_preview(session: Session, child: Child) -> NextWeekPreview | None:
    try:
        plan = prepare_daily_win_generation(session, child).plan
    except ContextUnavailableError:
        return None
    primary_code = plan.scheduled_goal_code or plan.primary_skill_code
    secondary = next(
        (
            code
            for code in plan.deferred_goals
            if is_academic_code(code) and code != primary_code
        ),
        None,
    )
    growth = plan.growth_target_code
    return NextWeekPreview(
        primary_academic_focus=display_name(
            plan.scheduled_goal_code or plan.primary_skill_code
        ),
        secondary_academic_focus=display_name(secondary) if secondary else None,
        growth_focus=(
            display_name(growth)
            if growth and is_growth_or_life_code(growth)
            else None
        ),
        why=plan.scheduler_why_selected
        or "Continue from the current scheduler and learner state.",
        scheduled_goal=plan.scheduled_goal_code,
    )


def _session_from_row(
    session: Session,
    win: DailyWin,
    feedback: DailyWinFeedback,
    skill: Skill,
) -> SessionEvidence:
    events = session.scalars(
        select(LearningEvent).where(
            LearningEvent.daily_win_id == win.id,
            LearningEvent.child_id == win.child_id,
        )
    ).all()
    observations: dict[str, str] = {}
    notice: list[str] = []
    for event in events:
        if event.event_type != EVENT_TYPE_SKILL_OBSERVATION:
            continue
        payload = event.payload if isinstance(event.payload, dict) else {}
        kind = str(payload.get("observation_type") or "")
        if kind == OBSERVATION_NOTICE:
            notice.extend(str(item) for item in (payload.get("chips") or []))
            continue
        signal = str(payload.get("signal") or "")
        if kind and signal:
            observations[kind] = signal
    plan_payload: dict[str, object] = {}
    mode = "practice"
    if win.instruction_plan_id is not None:
        plan_row = session.get(InstructionPlanRecord, win.instruction_plan_id)
        if plan_row is not None and isinstance(plan_row.plan, dict):
            plan_payload = plan_row.plan
            mode = str(
                plan_payload.get("instruction_mode") or plan_row.instruction_mode
            )
    bonus = plan_payload.get("bonus_challenge")
    bonus_dict = bonus if isinstance(bonus, dict) else {}
    return SessionEvidence(
        skill_code=skill.code,
        instruction_mode=mode,
        academic_result=feedback.academic_result,
        difficulty=feedback.difficulty,
        engagement=feedback.engagement,
        completion=feedback.completion,
        setback_response=feedback.setback_response,
        self_correction=observations.get(OBSERVATION_SELF_CORRECTION),
        strategy=observations.get(OBSERVATION_STRATEGY),
        performance_effort=observations.get(OBSERVATION_EFFORT),
        notice_chips=tuple(notice),
        bonus_category=(
            str(bonus_dict["category"]) if bonus_dict.get("category") else None
        ),
        bonus_engagement=observations.get(OBSERVATION_BONUS_ENGAGEMENT),
        non_target_error=observations.get(OBSERVATION_NON_TARGET),
        source_keys=(f"win-{str(win.id)[:8]}",),
        teach_the_coach=bool(plan_payload.get("teach_the_coach")),
        personal_best=bool(bonus_dict.get("personal_best")),
    )
