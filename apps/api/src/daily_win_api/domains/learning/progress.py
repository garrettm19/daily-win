from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.dev.presets import parent_goal_label
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.enums import PersistenceSignal, TrendDirection
from daily_win_api.domains.daily_wins.insight import parent_insight
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import DAILY_WIN_STATUS_READY
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.domains.learning.models import (
    ChildGoal,
    LearnerSkillState,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.presentation import (
    EVIDENCE_DISCLAIMER,
    STATE_GUIDE,
    academic_state_label,
    academic_supporting_copy,
    domain_label,
    session_evidence_label,
)
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_SKILL_OBSERVATION,
    map_setback_to_signal,
)
from daily_win_api.domains.learning.taxonomy import (
    is_academic_code,
    is_growth_or_life_code,
)

_PATTERN_COPY = {
    TrendDirection.IMPROVING.value: "Improving",
    TrendDirection.STABLE.value: "Stable",
    TrendDirection.DECLINING.value: "Needs more support",
}

_RECENT_OBSERVATION = {
    PersistenceSignal.INDEPENDENT_RETRY: "Returned to the challenge independently",
    PersistenceSignal.RETRY_AFTER_PROMPT: "Returned after one prompt",
    PersistenceSignal.SIGNIFICANT_SUPPORT: "Needed significant help after a setback",
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: "Stopped or avoided after a setback",
    PersistenceSignal.NO_SIGNAL: "No setback occurred",
}

_SIGNAL_TO_SETBACK = {
    PersistenceSignal.INDEPENDENT_RETRY.value: "kept_going_independently",
    PersistenceSignal.RETRY_AFTER_PROMPT.value: "continued_after_prompt",
    PersistenceSignal.SIGNIFICANT_SUPPORT.value: "needed_significant_help",
    PersistenceSignal.DISENGAGED_AFTER_SETBACK.value: "stopped_or_avoided",
    PersistenceSignal.NO_SIGNAL.value: "no_setback_occurred",
}

STILL_LEARNING = "Still learning — a few more Daily Wins will help establish a pattern."


class DemoGoalProgress(BaseModel):
    display_name: str
    latest_observation: str | None
    current_adjustment: str | None
    evidence_count: int
    evidence_label: str
    still_learning: bool
    still_learning_message: str | None = None
    recent_pattern: str | None = None


class DemoAcademicCheck(BaseModel):
    occurred_at: datetime
    result: str


class DemoAcademicProgress(BaseModel):
    domain_label: str
    skill_name: str
    state_label: str
    recent_evidence: str | None
    evidence_label: str
    session_count: int
    supporting_copy: str
    needs_review: bool = False
    band: str = "not_observed"
    recent_checks: list[DemoAcademicCheck] = []


class DemoResultSnapshot(BaseModel):
    difficulty: str | None = None
    academic_result: str | None = None
    setback_response: str | None = None
    completion: str | None = None
    engagement: str | None = None


class DemoStateGuideItem(BaseModel):
    label: str
    explanation: str


class DemoObservationRead(BaseModel):
    goal_name: str
    summary: str
    source: str


class DemoDailyWinSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    primary_focus: str
    has_feedback: bool
    is_adaptive: bool


class DemoProgressRead(BaseModel):
    nickname: str
    goals: list[DemoGoalProgress]
    academic_skills: list[DemoAcademicProgress] = []
    growth_skills: list[DemoGoalProgress] = []
    recent_observations: list[DemoObservationRead]
    recent_daily_wins: list[DemoDailyWinSummary]
    state_guide: list[DemoStateGuideItem] = []
    evidence_disclaimer: str | None = None


def load_demo_progress(session: Session, child: Child) -> DemoProgressRead:
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
    state_rows = session.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.household_id == child.household_id,
        )
    ).all()
    states = {skill.id: state for state, skill in state_rows}
    goals = [
        _goal_progress(child.nickname, skill, states.get(goal.skill_id))
        for goal, skill in goal_rows
    ]
    growth = [
        item
        for item, (_goal, skill) in zip(goals, goal_rows, strict=True)
        if is_growth_or_life_code(skill.code)
    ]
    academic = _academic_progress(state_rows, _academic_check_history(session, child))
    return DemoProgressRead(
        nickname=child.nickname,
        goals=goals,
        academic_skills=academic,
        growth_skills=growth,
        recent_observations=_recent_observations(session, child),
        recent_daily_wins=list_demo_daily_win_summaries(session, child, limit=10),
        state_guide=[
            DemoStateGuideItem(label=label, explanation=explanation)
            for label, explanation in STATE_GUIDE
        ]
        if academic
        else [],
        evidence_disclaimer=EVIDENCE_DISCLAIMER if academic else None,
    )


def list_demo_daily_win_summaries(
    session: Session, child: Child, *, limit: int = 20
) -> list[DemoDailyWinSummary]:
    rows = session.execute(
        select(DailyWin, Skill, DailyWinFeedback.id)
        .join(Skill, Skill.id == DailyWin.primary_skill_id)
        .outerjoin(DailyWinFeedback, DailyWinFeedback.daily_win_id == DailyWin.id)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(limit)
    ).all()
    summaries: list[DemoDailyWinSummary] = []
    for win, skill, feedback_id in rows:
        content = win.content if isinstance(win.content, dict) else {}
        summaries.append(
            DemoDailyWinSummary(
                id=win.id,
                title=win.title,
                created_at=win.created_at,
                primary_focus=parent_goal_label(skill.code, skill.display_name),
                has_feedback=feedback_id is not None,
                is_adaptive=bool(content.get("adaptation_summary")),
            )
        )
    return summaries


_RESULT_RECENT = {
    AcademicResult.CORRECT_INDEPENDENTLY: "Completed independently.",
    AcademicResult.CORRECT_AFTER_LIGHT_PROMPT: "Completed with a little help.",
    AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP: "Completed with a lot of help.",
    AcademicResult.INCORRECT: "Didn't get it yet.",
    AcademicResult.NOT_ATTEMPTED: "Didn't try this part.",
}


def _academic_progress(
    state_rows: list[tuple[LearnerSkillState, Skill]],
    check_history: dict[UUID, list[DemoAcademicCheck]],
) -> list[DemoAcademicProgress]:
    items: list[DemoAcademicProgress] = []
    for state, skill in state_rows:
        if not is_academic_code(skill.code):
            continue
        payload = state.state if isinstance(state.state, dict) else {}
        raw_band = payload.get("band")
        if not isinstance(raw_band, str):
            continue
        try:
            band = AcademicBand(raw_band)
        except ValueError:
            continue
        sessions = int(payload.get("distinct_session_count") or 0)
        if sessions == 0:
            continue
        needs = bool(payload.get("needs_remediation"))
        checks = check_history.get(skill.id, [])
        latest = None
        if checks:
            try:
                latest = AcademicResult(checks[0].result)
            except ValueError:
                latest = None
        items.append(
            DemoAcademicProgress(
                domain_label=domain_label(skill.domain),
                skill_name=skill.display_name,
                state_label=academic_state_label(band, needs_remediation=needs),
                recent_evidence=_recent_academic_evidence(latest),
                evidence_label=session_evidence_label(sessions),
                session_count=sessions,
                supporting_copy=academic_supporting_copy(
                    band, session_count=sessions, needs_remediation=needs
                ),
                needs_review=needs,
                band=band.value,
                recent_checks=checks[:6],
            )
        )
    return items


def _academic_check_history(
    session: Session, child: Child
) -> dict[UUID, list[DemoAcademicCheck]]:
    events = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
            LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
            LearningEvent.skill_id.is_not(None),
        )
        .order_by(LearningEvent.occurred_at.desc(), LearningEvent.created_at.desc())
        .limit(80)
    ).all()
    history: dict[UUID, list[DemoAcademicCheck]] = {}
    for event in events:
        if event.skill_id is None:
            continue
        payload = event.payload if isinstance(event.payload, dict) else {}
        raw = payload.get("result")
        if not isinstance(raw, str):
            continue
        try:
            AcademicResult(raw)
        except ValueError:
            continue
        bucket = history.setdefault(event.skill_id, [])
        if len(bucket) >= 6:
            continue
        bucket.append(
            DemoAcademicCheck(
                occurred_at=event.occurred_at or event.created_at,
                result=raw,
            )
        )
    return history


def _recent_academic_evidence(result: AcademicResult | None) -> str | None:
    if result is not None:
        return _RESULT_RECENT[result]
    return None


def _goal_progress(
    nickname: str, skill: Skill, state: LearnerSkillState | None
) -> DemoGoalProgress:
    count = 0 if state is None else state.evidence_count
    payload = state.state if state is not None and isinstance(state.state, dict) else {}
    signal = payload.get("latest_signal")
    direction = payload.get("direction")
    observation = None
    adjustment = None
    if count and isinstance(signal, str):
        setback = _SIGNAL_TO_SETBACK.get(signal)
        if setback is not None:
            insight = parent_insight(nickname, setback)
            observation = insight["observation"]
            adjustment = insight["next_adjustment"]
    still_learning = (
        count == 0
        or direction == TrendDirection.INSUFFICIENT_DATA.value
        or direction is None
    )
    pattern = None
    if count >= 3 and isinstance(direction, str) and direction in _PATTERN_COPY:
        pattern = _PATTERN_COPY[direction]
        still_learning = False
    if count == 0:
        label = "No observations yet"
    elif count == 1:
        label = "1 observation"
    else:
        label = f"{count} observations"
    still_message = STILL_LEARNING if still_learning else None
    if observation is None and still_learning:
        observation = STILL_LEARNING
    return DemoGoalProgress(
        display_name=parent_goal_label(skill.code, skill.display_name),
        latest_observation=observation,
        current_adjustment=adjustment,
        evidence_count=count,
        evidence_label=label,
        still_learning=still_learning,
        still_learning_message=still_message,
        recent_pattern=pattern,
    )


def _recent_observations(
    session: Session, child: Child, *, limit: int = 8
) -> list[DemoObservationRead]:
    events = list(
        session.scalars(
            select(LearningEvent)
            .where(
                LearningEvent.child_id == child.id,
                LearningEvent.household_id == child.household_id,
                LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION,
            )
            .order_by(LearningEvent.occurred_at.desc(), LearningEvent.created_at.desc())
            .limit(limit)
        )
    )
    if not events:
        return []
    skill_ids = [event.skill_id for event in events if event.skill_id is not None]
    win_ids = [event.daily_win_id for event in events if event.daily_win_id is not None]
    skills = (
        {
            skill.id: skill
            for skill in session.scalars(select(Skill).where(Skill.id.in_(skill_ids)))
        }
        if skill_ids
        else {}
    )
    wins = (
        {
            win.id: win
            for win in session.scalars(select(DailyWin).where(DailyWin.id.in_(win_ids)))
        }
        if win_ids
        else {}
    )
    items: list[DemoObservationRead] = []
    for event in events:
        summary = _event_parent_summary(event, skills, wins)
        if summary is not None:
            items.append(summary)
    return items


def _event_parent_summary(
    event: LearningEvent,
    skills: dict[UUID, Skill],
    wins: dict[UUID, DailyWin],
) -> DemoObservationRead | None:
    payload = event.payload if isinstance(event.payload, dict) else {}
    win = wins.get(event.daily_win_id) if event.daily_win_id is not None else None
    win_title = win.title if win is not None else None
    source = (
        f"From your reflection on {win_title}" if win_title else "From your reflection"
    )
    skill = skills.get(event.skill_id) if event.skill_id is not None else None
    if skill is None:
        return None
    skill_name = parent_goal_label(skill.code, skill.display_name)
    if skill.code == "growth.persistence":
        skill_name = "Persistence"
    elif skill.code == "writing.organization":
        skill_name = "Writing organization"
    raw = payload.get("signal")
    if not isinstance(raw, str):
        return None
    try:
        signal = map_setback_to_signal(raw)
        summary = _RECENT_OBSERVATION[signal]
    except (ValueError, KeyError):
        try:
            summary = _RECENT_OBSERVATION[PersistenceSignal(raw)]
        except ValueError:
            return None
    return DemoObservationRead(goal_name=skill_name, summary=summary, source=source)
