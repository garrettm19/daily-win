from datetime import UTC, datetime, timedelta

from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    AcademicEvidence,
    AcademicStateSnapshot,
)
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    PlannerInput,
    PlannerSkillState,
)

EVAL_NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def snapshot(
    band: AcademicBand,
    *,
    sessions: int = 1,
    practiced_days_ago: int | None = 0,
    independent_days_ago: int | None = None,
    needs_remediation: bool = False,
    now: datetime = EVAL_NOW,
) -> AcademicStateSnapshot:
    practiced = (
        None if practiced_days_ago is None else now - timedelta(days=practiced_days_ago)
    )
    independent = (
        None
        if independent_days_ago is None
        else now - timedelta(days=independent_days_ago)
    )
    return AcademicStateSnapshot(
        band=band,
        algorithm_version=ACADEMIC_PROJECTOR_V1,
        usable_evidence_count=max(sessions, 0),
        distinct_session_count=sessions,
        last_practiced_at=practiced,
        last_independent_success_at=independent,
        evidence_ids=(),
        summary="eval-fixture",
        needs_remediation=needs_remediation,
    )


def state(
    code: str,
    band: AcademicBand | None = None,
    *,
    sessions: int = 1,
    practiced_days_ago: int | None = 0,
    independent_days_ago: int | None = None,
    needs_remediation: bool = False,
    growth_signal: str | None = None,
) -> PlannerSkillState:
    academic = None
    if band is not None:
        academic = snapshot(
            band,
            sessions=sessions,
            practiced_days_ago=practiced_days_ago,
            independent_days_ago=independent_days_ago,
            needs_remediation=needs_remediation,
        )
    return PlannerSkillState(
        skill_code=code,
        academic=academic,
        latest_growth_signal=growth_signal,
    )


def planner_input(
    *,
    nickname: str = "Nova",
    age_years: int = 8,
    grade: str = "3",
    interests: tuple[str, ...] = ("space",),
    motivators: tuple[str, ...] = ("stories",),
    minutes: int = 20,
    goals: tuple[tuple[str, int], ...],
    states: tuple[PlannerSkillState, ...] = (),
    recent_skills: tuple[str, ...] = (),
    recent_themes: tuple[str, ...] = (),
    recent_modes: tuple[str, ...] = (),
    recent_goals: tuple[str, ...] = (),
    now: datetime = EVAL_NOW,
) -> PlannerInput:
    return PlannerInput(
        nickname=nickname,
        age_years=age_years,
        grade=grade,
        interests=interests,
        motivators=motivators,
        preferred_duration_minutes=minutes,
        goals=tuple(GoalPriority(code, priority) for code, priority in goals),
        states={item.skill_code: item for item in states},
        recent_skill_codes=recent_skills,
        recent_themes=recent_themes,
        now=now,
        recent_instruction_modes=recent_modes,
        recent_goal_codes=recent_goals,
    )


def evidence(
    result: AcademicResult,
    *,
    day: int,
    session: str,
    now: datetime = EVAL_NOW,
) -> AcademicEvidence:
    return AcademicEvidence(
        event_id=None,
        occurred_at=now + timedelta(days=day),
        result=result,
        session_key=session,
    )
