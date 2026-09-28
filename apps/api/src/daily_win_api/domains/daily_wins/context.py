from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import (
    ContextManifest,
    DailyWinModelContext,
    EvidenceSummaryContext,
    InstructionPlanContext,
    Material,
    ParentReportedBaselineContext,
)
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.latency import span
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.daily_wins.renderer_contract import plan_with_contracts
from daily_win_api.domains.daily_wins.schemas import (
    BOUNDED_EVIDENCE_CAP,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    RECENT_DAILY_WINS_CAP,
    RECENT_LEARNING_EVENTS_CAP,
    RECENT_THEMES_CAP,
    ContextUnavailableError,
)
from daily_win_api.domains.learning.academic import (
    EVENT_TYPE_SKILL_ASSESSMENT,
    AcademicStateSnapshot,
)
from daily_win_api.domains.learning.bonus import low_engagement_categories_from_payloads
from daily_win_api.domains.learning.enums import AcademicBand
from daily_win_api.domains.learning.models import (
    ChildGoal,
    InstructionPlanRecord,
    LearnerSkillState,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    InstructionPlan,
    PlannerInput,
    PlannerSkillState,
    plan_as_dict,
    plan_instruction,
)
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_DAILY_WIN_FEEDBACK,
    EVENT_TYPE_SKILL_OBSERVATION,
    map_setback_to_signal,
)
from daily_win_api.domains.learning.taxonomy import is_academic_code, strand_code_for


@dataclass(frozen=True)
class GenerationPrep:
    plan: InstructionPlan
    context: DailyWinModelContext
    manifest: ContextManifest


def build_daily_win_context(
    session: Session, child: Child
) -> tuple[DailyWinModelContext, ContextManifest]:
    prep = prepare_daily_win_generation(session, child)
    return prep.context, prep.manifest


def prepare_daily_win_generation(session: Session, child: Child) -> GenerationPrep:
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

    states = _planner_states(session, child)
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
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
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
    recent_themes = tuple(win.title for win in prior_wins[:RECENT_THEMES_CAP])
    recent_skill_codes = tuple(
        prior_skills[win.primary_skill_id].code
        for win in prior_wins
        if win.primary_skill_id in prior_skills
    )
    history = load_recent_instruction_history(session, child)
    plan = plan_instruction(
        PlannerInput(
            nickname=child.nickname,
            age_years=baseline.age_years,
            grade=baseline.grade,
            interests=tuple(baseline.interests),
            motivators=tuple(baseline.motivators),
            preferred_duration_minutes=baseline.preferred_activity_minutes,
            goals=tuple(
                GoalPriority(skill_code=skill.code, priority=goal.priority)
                for goal, skill in goal_rows
            ),
            states=states,
            recent_skill_codes=history[0] or recent_skill_codes,
            recent_themes=recent_themes,
            now=_aware_now(events, prior_wins),
            recent_instruction_modes=history[1],
            recent_goal_codes=history[2],
            low_engagement_categories=low_engagement_categories_from_payloads(
                tuple(
                    event.payload
                    for event in events
                    if isinstance(event.payload, dict)
                )
            ),
        )
    )
    allowed = _allowed_from_plan(plan)
    evidence = _bounded_evidence(events, event_skills)
    with span("prompt_context"):
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
            instruction_plan=instruction_plan_context(plan),
            bounded_evidence_summaries=evidence,
            recent_themes=list(recent_themes),
            allowed_skill_codes=allowed,
            allowed_materials=[material.value for material in Material],
        )
    skill_state_ids = [
        row.id
        for row in session.scalars(
            select(LearnerSkillState).where(
                LearnerSkillState.child_id == child.id,
                LearnerSkillState.household_id == child.household_id,
            )
        )
    ]
    manifest = ContextManifest(
        child_id=child.id,
        household_id=child.household_id,
        baseline_id=baseline.id,
        goal_ids=[goal.id for goal, _skill in goal_rows],
        skill_state_ids=skill_state_ids,
        learning_event_ids=[event.id for event in events[:BOUNDED_EVIDENCE_CAP]],
        prior_daily_win_ids=[win.id for win in prior_wins[:RECENT_THEMES_CAP]],
        prompt_version=PROMPT_VERSION,
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
    )
    return GenerationPrep(plan=plan, context=context, manifest=manifest)


def instruction_plan_context(plan: InstructionPlan) -> InstructionPlanContext:
    payload = plan_as_dict(plan)
    return plan_with_contracts(InstructionPlanContext.model_validate(payload))


def _allowed_from_plan(plan: InstructionPlan) -> list[str]:
    codes = [plan.primary_skill_code]
    for extra in (plan.supporting_skill_code, plan.growth_target_code):
        if extra and extra not in codes:
            codes.append(extra)
    return codes


def _planner_states(session: Session, child: Child) -> dict[str, PlannerSkillState]:
    rows = session.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.household_id == child.household_id,
        )
    ).all()
    states: dict[str, PlannerSkillState] = {}
    for state, skill in rows:
        payload = state.state if isinstance(state.state, dict) else {}
        academic = None
        raw_band = payload.get("band")
        if is_academic_code(skill.code) and isinstance(raw_band, str):
            try:
                band = AcademicBand(raw_band)
            except ValueError:
                band = AcademicBand.NOT_OBSERVED
            academic = AcademicStateSnapshot(
                band=band,
                algorithm_version=state.algorithm_version,
                usable_evidence_count=int(payload.get("usable_evidence_count") or 0),
                distinct_session_count=int(payload.get("distinct_session_count") or 0),
                last_practiced_at=_parse_dt(payload.get("last_practiced_at")),
                last_independent_success_at=_parse_dt(
                    payload.get("last_independent_success_at")
                ),
                evidence_ids=(),
                summary=str(payload.get("summary") or ""),
                needs_remediation=bool(payload.get("needs_remediation")),
            )
        latest = payload.get("latest_signal")
        states[skill.code] = PlannerSkillState(
            skill_code=skill.code,
            academic=academic,
            latest_growth_signal=str(latest) if latest is not None else None,
        )
    return states


def _bounded_evidence(
    events: list[LearningEvent], event_skills: dict
) -> list[EvidenceSummaryContext]:
    summaries: list[EvidenceSummaryContext] = []
    for event in events:
        if event.event_type not in {
            EVENT_TYPE_SKILL_OBSERVATION,
            EVENT_TYPE_SKILL_ASSESSMENT,
            EVENT_TYPE_DAILY_WIN_FEEDBACK,
        }:
            continue
        skill_code = (
            event_skills[event.skill_id].code
            if event.skill_id is not None and event.skill_id in event_skills
            else "unspecified"
        )
        reporting = (
            "measurement" if event.evidence_kind == "MEASUREMENT" else "parent_reported"
        )
        summaries.append(
            EvidenceSummaryContext(
                skill_code=skill_code,
                summary=_event_summary(
                    event, None if skill_code == "unspecified" else skill_code
                ),
                reporting_kind=reporting,
            )
        )
        if len(summaries) >= BOUNDED_EVIDENCE_CAP:
            break
    return summaries


def _aware_now(events: list[LearningEvent], wins: list[DailyWin]) -> datetime:
    from datetime import UTC
    from datetime import datetime as dt

    stamps = [event.occurred_at for event in events] + [win.created_at for win in wins]
    return max(stamps) if stamps else dt.now(UTC)


def load_recent_instruction_history(
    session: Session, child: Child, *, limit: int = 8, before=None
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    stmt = (
        select(InstructionPlanRecord)
        .where(
            InstructionPlanRecord.child_id == child.id,
            InstructionPlanRecord.household_id == child.household_id,
        )
        .order_by(InstructionPlanRecord.created_at.desc())
        .limit(limit)
    )
    if before is not None:
        stmt = stmt.where(InstructionPlanRecord.created_at < before)
    rows = session.scalars(stmt).all()
    skills: list[str] = []
    modes: list[str] = []
    goals: list[str] = []
    skill_ids = [row.primary_skill_id for row in rows]
    by_id = (
        {
            skill.id: skill
            for skill in session.scalars(select(Skill).where(Skill.id.in_(skill_ids)))
        }
        if skill_ids
        else {}
    )
    for row in rows:
        skill = by_id.get(row.primary_skill_id)
        payload = row.plan if isinstance(row.plan, dict) else {}
        code = (
            skill.code
            if skill is not None
            else str(payload.get("primary_skill_code") or "")
        )
        if not code:
            continue
        skills.append(code)
        modes.append(row.instruction_mode)
        scheduled = payload.get("scheduled_goal_code")
        if isinstance(scheduled, str) and scheduled:
            goals.append(scheduled)
        else:
            goals.append(strand_code_for(code))
    return tuple(skills), tuple(modes), tuple(goals)


def _parse_dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        from datetime import UTC

        stamp = stamp.replace(tzinfo=UTC)
    return stamp


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
        return f"Most recent parent observation for {label}: {phrases[mapped.value]}."
    if event.event_type == EVENT_TYPE_SKILL_ASSESSMENT:
        result = payload.get("result")
        label = skill_code or "the target skill"
        return f"Structured measurement for {label}: {result}."
    if event.event_type == EVENT_TYPE_DAILY_WIN_FEEDBACK:
        return "Parent reported how the Daily Win went."
    return "Parent-reported learning event."
