from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import (
    ContextManifest,
    DailyWinModelContext,
    GoalContext,
    LearningEventContext,
    Material,
    ParentReportedBaselineContext,
    PriorDailyWinContext,
    SkillStateContext,
)
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.adaptation import build_adaptation_directive
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    RECENT_DAILY_WINS_CAP,
    RECENT_LEARNING_EVENTS_CAP,
    ContextUnavailableError,
)
from daily_win_api.domains.learning.models import (
    ChildGoal,
    LearnerSkillState,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_DAILY_WIN_FEEDBACK,
    EVENT_TYPE_SKILL_OBSERVATION,
    PERSISTENCE_SKILL_CODE,
    map_setback_to_signal,
)


def build_daily_win_context(
    session: Session, child: Child
) -> tuple[DailyWinModelContext, ContextManifest]:
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
        raise ContextUnavailableError

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
    if not goal_rows:
        raise ContextUnavailableError

    goal_skill_ids = [goal.skill_id for goal, _skill in goal_rows]
    skill_states = session.scalars(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.household_id == child.household_id,
            LearnerSkillState.skill_id.in_(goal_skill_ids),
        )
    ).all()
    skill_by_id = {
        skill.id: skill
        for skill in session.scalars(select(Skill).where(Skill.id.in_(goal_skill_ids)))
    }

    events = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
        )
        .order_by(LearningEvent.occurred_at.desc(), LearningEvent.created_at.desc())
        .limit(RECENT_LEARNING_EVENTS_CAP)
    ).all()
    event_skill_ids = [event.skill_id for event in events if event.skill_id is not None]
    event_skills = (
        {
            skill.id: skill
            for skill in session.scalars(
                select(Skill).where(Skill.id.in_(event_skill_ids))
            )
        }
        if event_skill_ids
        else {}
    )

    prior_wins = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc())
        .limit(RECENT_DAILY_WINS_CAP)
    ).all()
    prior_skill_ids = [win.primary_skill_id for win in prior_wins]
    prior_skills = (
        {
            skill.id: skill
            for skill in session.scalars(
                select(Skill).where(Skill.id.in_(prior_skill_ids))
            )
        }
        if prior_skill_ids
        else {}
    )

    allowed_skills = list(
        session.scalars(select(Skill.code).where(Skill.active.is_(True)))
    )
    primary_skill_code = goal_rows[0][1].code

    learner_skill_states = [
        _skill_state_context(state, skill_by_id[state.skill_id])
        for state in skill_states
        if state.skill_id in skill_by_id
    ]
    persistence_state = next(
        (
            item
            for item in learner_skill_states
            if item.skill_code == PERSISTENCE_SKILL_CODE
        ),
        None,
    )
    adaptation_directive = build_adaptation_directive(
        skill_code=PERSISTENCE_SKILL_CODE,
        latest_signal=persistence_state.latest_signal if persistence_state else None,
        nickname=child.nickname,
    )

    context = DailyWinModelContext(
        nickname=child.nickname,
        parent_reported_baseline=ParentReportedBaselineContext(
            age_years=baseline.age_years,
            grade=baseline.grade,
            interests=list(baseline.interests),
            strengths=list(baseline.strengths),
            current_difficulties=list(baseline.current_difficulties),
            motivators=list(baseline.motivators),
            response_to_difficulty=baseline.response_to_difficulty,
            preferred_activity_minutes=baseline.preferred_activity_minutes,
        ),
        active_goals=[
            GoalContext(
                priority=goal.priority,
                skill_code=skill.code,
                display_name=skill.display_name,
                domain=skill.domain,
            )
            for goal, skill in goal_rows
        ],
        primary_goal_skill_code=primary_skill_code,
        learner_skill_states=learner_skill_states,
        recent_learning_events=[
            LearningEventContext(
                evidence_kind=event.evidence_kind,
                source=event.source,
                event_type=event.event_type,
                skill_code=(
                    event_skills[event.skill_id].code
                    if event.skill_id is not None and event.skill_id in event_skills
                    else None
                ),
                occurred_at=event.occurred_at,
                summary=_event_summary(
                    event,
                    event_skills[event.skill_id].code
                    if event.skill_id is not None and event.skill_id in event_skills
                    else None,
                ),
            )
            for event in events
        ],
        recent_daily_wins=[
            PriorDailyWinContext(
                title=win.title,
                primary_skill_code=prior_skills[win.primary_skill_id].code,
                objective=win.objective,
            )
            for win in prior_wins
            if win.primary_skill_id in prior_skills
        ],
        adaptation_directive=adaptation_directive,
        allowed_skill_codes=allowed_skills,
        allowed_materials=[material.value for material in Material],
    )
    manifest = ContextManifest(
        child_id=child.id,
        household_id=child.household_id,
        baseline_id=baseline.id,
        goal_ids=[goal.id for goal, _skill in goal_rows],
        skill_state_ids=[state.id for state in skill_states],
        learning_event_ids=[event.id for event in events],
        prior_daily_win_ids=[win.id for win in prior_wins],
        prompt_version=PROMPT_VERSION,
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
    )
    return context, manifest


def _skill_state_context(state: LearnerSkillState, skill: Skill) -> SkillStateContext:
    payload = state.state if isinstance(state.state, dict) else {}
    latest = payload.get("latest_signal")
    direction = payload.get("direction")
    summary = payload.get("summary")
    return SkillStateContext(
        skill_code=skill.code,
        evidence_count=state.evidence_count,
        confidence=state.confidence,
        has_derived_state=bool(state.state),
        latest_signal=str(latest) if latest is not None else None,
        direction=str(direction) if direction is not None else None,
        summary=str(summary) if summary is not None else None,
    )


def _event_summary(event: LearningEvent, skill_code: str | None) -> str:
    payload = event.payload if isinstance(event.payload, dict) else {}
    if event.event_type == EVENT_TYPE_SKILL_OBSERVATION:
        raw_signal = payload.get("signal")
        label = skill_code or "the current goal"
        try:
            mapped = map_setback_to_signal(str(raw_signal))
        except (ValueError, KeyError, TypeError):
            return f"Parent observation for {label}."
        phrases = {
            "independent_retry": "child returned to the task independently",
            "retry_after_prompt": "child returned to the task after one prompt",
            "significant_support": "child needed significant help after a setback",
            "disengaged_after_setback": "child stopped or avoided after a setback",
            "no_signal": "no setback occurred",
        }
        return (
            f"Most recent parent observation for {label}: "
            f"{phrases[mapped.value]}."
        )
    if event.event_type == EVENT_TYPE_DAILY_WIN_FEEDBACK:
        return "Parent reported how the Daily Win went."
    return "Parent-reported learning event."
