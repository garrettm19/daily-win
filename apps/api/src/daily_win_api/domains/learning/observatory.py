"""Development-only learning-engine observatory.

Backend-authoritative traces. Never include secrets, DB UUIDs, raw prompts,
or chain-of-thought.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, get_settings
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.context import (
    load_recent_instruction_history,
    prepare_daily_win_generation,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.renderer_contract import (
    FRESH_ASSESSMENT_ITEM,
    contracts_for_plan,
)
from daily_win_api.domains.daily_wins.safety import SAFETY_VALIDATOR_VERSION
from daily_win_api.domains.daily_wins.schemas import (
    BOUNDED_EVIDENCE_CAP,
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    RECENT_DAILY_WINS_CAP,
    ContextUnavailableError,
)
from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    EVENT_TYPE_SKILL_ASSESSMENT,
    AcademicEvidence,
    AcademicResult,
    AcademicStateSnapshot,
    project_academic_band,
)
from daily_win_api.domains.learning.bonus import low_engagement_categories_from_payloads
from daily_win_api.domains.learning.coach_protocol import COACH_PROTOCOL_V1
from daily_win_api.domains.learning.enums import AcademicBand, InstructionMode
from daily_win_api.domains.learning.explanations import (
    display_name,
    next_win_implication,
    preview_reason,
    why_not_explanations,
)
from daily_win_api.domains.learning.models import (
    ChildGoal,
    InstructionPlanRecord,
    LearnerSkillState,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.observatory_schemas import (
    AcademicSnapshotItem,
    AssessmentPlanTrace,
    CoachProtocolTrace,
    ContextBudgetComponent,
    CurriculumDecisionTrace,
    CurriculumGraphNode,
    CurriculumGraphTrace,
    EngineVersionReport,
    FirstWinTimingTrace,
    GenerationFailureTrace,
    GenerationPerformanceTrace,
    GrowthSnapshotItem,
    InstructionPlanTrace,
    LearnerSnapshot,
    LearningQaBundle,
    LearningTrace,
    NextWinPreparationTrace,
    NextWinPreview,
    PlacementTrace,
    PriorEvidenceTrace,
    ProfileContextTrace,
    RedactedContextReport,
    ReflectionTrace,
    RendererTrace,
    SchedulerTrace,
    SkillStateDelta,
    WeeklyContextTrace,
)
from daily_win_api.domains.learning.placement import (
    PLACEMENT_POLICY_CURRENT,
    decide_placement,
)
from daily_win_api.domains.learning.planner import (
    INSTRUCTION_POLICY_CURRENT,
    GoalPriority,
    InstructionPlan,
    PlannerInput,
    PlannerSkillState,
    plan_from_dict,
    plan_instruction,
)
from daily_win_api.domains.learning.prerequisites import prerequisites_for
from daily_win_api.domains.learning.presentation import (
    academic_state_label,
    domain_label,
)
from daily_win_api.domains.learning.probes import PROBE_CATALOG_VERSION
from daily_win_api.domains.learning.scheduler import INSTRUCTION_SCHEDULER_V1
from daily_win_api.domains.learning.signals import (
    PERSISTENCE_SKILL_CODE,
    TREND_PROJECTOR_V1,
)
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import (
    TAXONOMY_VERSION,
    definition_by_code,
    is_academic_code,
    is_growth_or_life_code,
)

TRACE_FAILURE_CODES = frozenset(
    {
        "configuration_error",
        "provider_error",
        "schema_error",
        "unsafe_content",
        "renderer_contract_failed",
        "duplicate_generation",
        "instruction_plan_mismatch",
    }
)

_API_TO_TRACE = {
    "schema_validation_failed": "schema_error",
    "feedback_required": "duplicate_generation",
    "harmful_content": "unsafe_content",
}

_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_SECRET = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}|openai_api_key|x-demo-session|"
    r"\bsystem_prompt\b|chain[-_ ]of[-_ ]thought|private[-_ ]notes?",
    re.IGNORECASE,
)
_STANDARD = {item["skill_code"]: item["standard_code"] for item in SKILL_STANDARD_REFS}


def trace_failure_code(api_code: str | None) -> str | None:
    if not api_code:
        return None
    mapped = _API_TO_TRACE.get(api_code, api_code)
    return mapped if mapped in TRACE_FAILURE_CODES else mapped


def failure_summary(code: str) -> str:
    return {
        "configuration_error": (
            "Generation could not start because the model provider is not configured."
        ),
        "provider_error": "The model provider failed. No Daily Win was saved.",
        "schema_error": "The model response did not match the required schema.",
        "unsafe_content": (
            "Application safety rules rejected the generated activity."
        ),
        "renderer_contract_failed": (
            "The generated activity failed a required renderer contract."
        ),
        "duplicate_generation": (
            "A Daily Win is already waiting for reflection, so a duplicate "
            "was not created."
        ),
        "instruction_plan_mismatch": (
            "The generated activity did not follow the InstructionPlan."
        ),
    }.get(code, "Generation did not complete.")


def engine_version_report() -> EngineVersionReport:
    return EngineVersionReport(
        curriculum_version=TAXONOMY_VERSION,
        placement_policy=PLACEMENT_POLICY_CURRENT,
        instruction_policy=INSTRUCTION_POLICY_CURRENT,
        instruction_scheduler=INSTRUCTION_SCHEDULER_V1,
        academic_projector=ACADEMIC_PROJECTOR_V1,
        growth_projector=TREND_PROJECTOR_V1,
        prompt_version=PROMPT_VERSION,
        renderer_model=get_settings().openai_model or DEFAULT_OPENAI_MODEL,
        renderer_schema_version=f"in{INPUT_SCHEMA_VERSION}/out{OUTPUT_SCHEMA_VERSION}/content{CONTENT_SCHEMA_VERSION}",
        safety_validator_version=SAFETY_VALIDATOR_VERSION,
        probe_catalog_version=PROBE_CATALOG_VERSION,
        coach_protocol=COACH_PROTOCOL_V1,
    )


def build_learning_qa(session: Session, child: Child) -> LearningQaBundle:
    snapshot = build_learner_snapshot(session, child)
    latest = _latest_win(session, child)
    trace = None
    preview = None
    graph = CurriculumGraphTrace(strand="", target_skill=None, nodes=[])
    has_feedback = False
    title = None
    try:
        if latest is not None:
            trace = build_learning_trace(session, child, latest.id)
            title = latest.title
            has_feedback = _feedback_for(session, latest.id) is not None
        preview = build_next_win_preview(session, child)
        graph = build_curriculum_graph(
            session,
            child,
            target_skill=preview.likely_target if preview else None,
        )
    except ContextUnavailableError:
        return LearningQaBundle(
            engine=engine_version_report(),
            snapshot=snapshot,
            graph=graph,
            setup_required=True,
        )
    from daily_win_api.domains.daily_wins.first_win import first_win_timing_snapshot
    from daily_win_api.domains.daily_wins.preparation import (
        generation_performance_snapshot,
        read_next_win_preparation,
    )

    preparation = read_next_win_preparation(session, child)
    performance = generation_performance_snapshot(session, child)
    timing = first_win_timing_snapshot(session, child)
    return LearningQaBundle(
        engine=engine_version_report(),
        snapshot=snapshot,
        graph=graph,
        latest_trace=trace,
        next_preview=preview,
        latest_win_title=title,
        latest_has_feedback=has_feedback,
        next_win_preparation=NextWinPreparationTrace(
            status=preparation.status,
            trigger=preparation.trigger,
            generated_after_reflection=preparation.generated_after_reflection,
            attempt_count=preparation.attempt_count,
            error_code=preparation.error_code,
            model=preparation.model,
            prompt_version=preparation.prompt_version,
            latency_ms=preparation.latency_ms,
            plan_valid=preparation.plan_valid,
        ),
        generation_performance=GenerationPerformanceTrace.model_validate(performance),
        first_win_timing=FirstWinTimingTrace.model_validate(timing),
    )


def build_learning_trace(
    session: Session,
    child: Child,
    daily_win_id: UUID | None = None,
) -> LearningTrace:
    win = None
    if daily_win_id is not None:
        win = session.scalar(
            select(DailyWin).where(
                DailyWin.id == daily_win_id,
                DailyWin.child_id == child.id,
                DailyWin.household_id == child.household_id,
            )
        )
    else:
        win = _latest_win(session, child)
    if win is None:
        return _failed_or_empty_trace(session, child)

    plan_row = None
    if win.instruction_plan_id is not None:
        plan_row = session.get(InstructionPlanRecord, win.instruction_plan_id)
    plan = plan_from_dict(plan_row.plan) if plan_row and plan_row.plan else None
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    feedback = _feedback_for(session, win.id)
    before = _planner_input_as_of(session, child, win.created_at)
    if plan is None:
        plan = plan_instruction(before)
    placement = decide_placement(
        _primary_academic_goal(before), before.age_years, before.states
    )
    after_states = before.states
    if feedback is not None:
        after_input = _planner_input_as_of(session, child, feedback.submitted_at)
        after_states = after_input.states
    upcoming = plan_instruction(
        _planner_input_as_of(
            session,
            child,
            feedback.submitted_at if feedback is not None else win.created_at,
        )
    )
    evidence_result = feedback.academic_result if feedback is not None else None
    prior = _prior_evidence(before, plan)
    renderer, failure = _renderer_trace(run, plan, win)
    status = "succeeded"
    if failure is not None:
        status = "failed"
    elif feedback is None:
        latest = _latest_win(session, child)
        if latest is not None and latest.id == win.id:
            status = "succeeded"
    trace = LearningTrace(
        generation_status=status,
        profile=_profile_trace(before),
        placement=_placement_trace(placement, plan),
        scheduler=_scheduler_trace(plan),
        relevant_prior_evidence=prior,
        curriculum=_curriculum_trace(plan, before),
        instruction_plan=_plan_trace(plan),
        assessment=_assessment_trace(plan),
        renderer=renderer,
        reflection=_reflection_trace(feedback),
        state_update=_state_deltas(plan, before.states, after_states, evidence_result),
        next_win_implication=next_win_implication(
            previous=plan,
            upcoming=upcoming,
            evidence_result=evidence_result,
        ),
        why_not=why_not_explanations(plan, before),
        generation_failure=failure,
        win_created_at=win.created_at,
        win_title=win.title,
        coach_protocol=_coach_trace(plan),
        weekly_context=_weekly_trace(plan),
        next_win_preparation=_preparation_trace(session, child),
    )
    assert_trace_is_safe(trace)
    return trace


def build_next_win_preview(session: Session, child: Child) -> NextWinPreview:
    prep = prepare_daily_win_generation(session, child)
    plan = prep.plan
    return NextWinPreview(
        likely_target=plan.primary_skill_code,
        likely_parent_friendly_name=display_name(plan.primary_skill_code),
        likely_mode=plan.instruction_mode.value,
        likely_scaffold=plan.scaffold_level.value,
        likely_difficulty=plan.intended_difficulty,
        reason=preview_reason(plan),
        scheduled_goal=plan.scheduled_goal_code,
        scheduler_reason=plan.scheduler_why_selected,
    )


def build_learner_snapshot(session: Session, child: Child) -> LearnerSnapshot:
    rows = session.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.household_id == child.household_id,
        )
        .order_by(Skill.domain.asc(), Skill.code.asc())
    ).all()
    academic: list[AcademicSnapshotItem] = []
    growth: list[GrowthSnapshotItem] = []
    for state, skill in rows:
        payload = state.state if isinstance(state.state, dict) else {}
        if is_academic_code(skill.code):
            band = str(payload.get("band") or AcademicBand.NOT_OBSERVED.value)
            academic.append(
                AcademicSnapshotItem(
                    domain_label=domain_label(skill.domain),
                    skill_name=skill.display_name,
                    skill_code=skill.code,
                    band=band,
                    band_label=academic_state_label(AcademicBand(band)),
                    session_count=int(payload.get("distinct_session_count") or 0),
                    latest_result=_latest_result_label(session, child, skill.id),
                    last_independent=_date_label(
                        payload.get("last_independent_success_at")
                    ),
                )
            )
        elif is_growth_or_life_code(skill.code):
            growth.append(
                GrowthSnapshotItem(
                    skill_name=skill.display_name,
                    skill_code=skill.code,
                    latest_signal=(
                        str(payload["latest_signal"])
                        if payload.get("latest_signal")
                        else None
                    ),
                    summary=str(payload.get("summary") or ""),
                )
            )
    return LearnerSnapshot(nickname=child.nickname, academic=academic, growth=growth)


def build_curriculum_graph(
    session: Session,
    child: Child,
    *,
    target_skill: str | None = None,
) -> CurriculumGraphTrace:
    if target_skill is None:
        try:
            target_skill = build_next_win_preview(session, child).likely_target
        except ContextUnavailableError:
            target_skill = None
    catalog = definition_by_code()
    strand = ""
    if target_skill and target_skill in catalog:
        strand = str(catalog[target_skill].get("strand") or "")
    states = _current_academic_states(session, child)
    nodes: list[CurriculumGraphNode] = []
    for code, definition in catalog.items():
        if str(definition.get("strand") or "") != strand:
            continue
        if definition.get("skill_kind") == "strand":
            continue
        snapshot = states.get(code)
        band = snapshot.band.value if snapshot else AcademicBand.NOT_OBSERVED.value
        prereqs = prerequisites_for(code)
        blocked = any(
            states.get(item) is None
            or states[item].band
            not in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}
            for item in prereqs
        )
        nodes.append(
            CurriculumGraphNode(
                skill_code=code,
                parent_friendly_name=str(definition["display_name"]),
                band=band,
                is_target=code == target_skill,
                is_blocked=blocked and code == target_skill,
                is_retained=band == AcademicBand.RETAINED.value,
            )
        )
    nodes.sort(
        key=lambda item: catalog[item.skill_code].get("progression_position") or 0
    )
    return CurriculumGraphTrace(strand=strand, target_skill=target_skill, nodes=nodes)


def build_redacted_context(session: Session, child: Child) -> RedactedContextReport:
    prep = prepare_daily_win_generation(session, child)
    payload = prep.context.model_dump(mode="json")
    redacted = _redact_value(payload)
    serialized = json.dumps(redacted, default=str)
    plan_json = json.dumps(payload.get("instruction_plan") or {}, default=str)
    profile_json = json.dumps(
        payload.get("parent_reported_baseline") or {}, default=str
    )
    evidence_json = json.dumps(
        payload.get("bounded_evidence_summaries") or [], default=str
    )
    wins_json = json.dumps(payload.get("recent_themes") or [], default=str)
    prompt_chars = len(PROMPT_VERSION) + 1800
    components = [
        ContextBudgetComponent(
            name="profile",
            characters=len(profile_json),
            estimated_tokens=_est_tokens(len(profile_json)),
        ),
        ContextBudgetComponent(
            name="InstructionPlan",
            characters=len(plan_json),
            estimated_tokens=_est_tokens(len(plan_json)),
        ),
        ContextBudgetComponent(
            name="evidence_summaries",
            characters=len(evidence_json),
            estimated_tokens=_est_tokens(len(evidence_json)),
        ),
        ContextBudgetComponent(
            name="recent_wins",
            characters=len(wins_json),
            estimated_tokens=_est_tokens(len(wins_json)),
        ),
        ContextBudgetComponent(
            name="prompt_instructions",
            characters=prompt_chars,
            estimated_tokens=_est_tokens(prompt_chars),
        ),
    ]
    report = RedactedContextReport(
        events_included=min(
            len(prep.context.bounded_evidence_summaries), BOUNDED_EVIDENCE_CAP
        ),
        prior_wins_included=min(
            len(prep.context.recent_themes), RECENT_DAILY_WINS_CAP
        ),
        profile_fields_included=[
            "nickname",
            "age_years",
            "grade",
            "interests",
            "motivators",
            "preferred_activity_minutes",
        ],
        planner_fields_included=[
            "primary_skill_code",
            "instruction_mode",
            "scaffold_level",
            "assessment_objective",
            "reason_codes",
        ],
        serialized_characters=len(serialized),
        estimated_tokens=_est_tokens(len(serialized) + prompt_chars),
        components=components,
        redacted_context=redacted if isinstance(redacted, dict) else {},
    )
    assert_trace_is_safe(report)
    return report


def assert_trace_is_safe(payload: object) -> None:
    if hasattr(payload, "model_dump"):
        blob = json.dumps(payload.model_dump(mode="json"), default=str)
    elif isinstance(payload, str):
        blob = payload
    else:
        blob = json.dumps(payload, default=str)
    if _UUID.search(blob):
        raise AssertionError("observatory payload leaked a UUID")
    if _SECRET.search(blob):
        raise AssertionError("observatory payload leaked a secret or prompt")


def _est_tokens(characters: int) -> int:
    return max(1, characters // 4)


def _failed_or_empty_trace(session: Session, child: Child) -> LearningTrace:
    try:
        data = _planner_input_as_of(session, child, datetime.now().astimezone())
    except ContextUnavailableError:
        raise
    plan = plan_instruction(data)
    placement = decide_placement(
        _primary_academic_goal(data), data.age_years, data.states
    )
    latest_run = session.scalars(
        select(AiRun)
        .where(AiRun.child_id == child.id, AiRun.household_id == child.household_id)
        .order_by(AiRun.created_at.desc())
        .limit(1)
    ).first()
    renderer, failure = _renderer_trace(latest_run, plan, None)
    latest_win = _latest_win(session, child)
    status = "failed" if failure else "duplicate_blocked" if latest_win else "idle"
    if latest_win is not None and _feedback_for(session, latest_win.id) is None:
        failure = GenerationFailureTrace(
            reason_code="duplicate_generation",
            parent_safe_summary=failure_summary("duplicate_generation"),
        )
        status = "duplicate_blocked"
    trace = LearningTrace(
        generation_status=status,
        profile=_profile_trace(data),
        placement=_placement_trace(placement, plan),
        relevant_prior_evidence=_prior_evidence(data, plan),
        curriculum=_curriculum_trace(plan, data),
        instruction_plan=_plan_trace(plan),
        assessment=_assessment_trace(plan),
        renderer=renderer,
        why_not=why_not_explanations(plan, data),
        next_win_implication="No Daily Win is stored yet.",
        generation_failure=failure,
        coach_protocol=_coach_trace(plan),
        weekly_context=_weekly_trace(plan),
        next_win_preparation=_preparation_trace(session, child),
    )
    assert_trace_is_safe(trace)
    return trace


def _profile_trace(data: PlannerInput) -> ProfileContextTrace:
    return ProfileContextTrace(
        nickname=data.nickname,
        age_years=data.age_years,
        grade=data.grade,
        selected_goals=[goal.skill_code for goal in data.goals],
        relevant_interests=list(data.interests[:4]),
        preferred_duration_minutes=data.preferred_duration_minutes,
    )


def _placement_trace(placement, plan: InstructionPlan) -> PlacementTrace:
    strand = str(
        definition_by_code().get(plan.primary_skill_code, {}).get("strand") or ""
    )
    mode = "sparse_diagnostic" if placement.sparse_evidence else "evidence_driven"
    if plan.instruction_mode is InstructionMode.DIAGNOSTIC:
        mode = "grade_band_diagnostic"
    return PlacementTrace(
        placement_policy_version=placement.policy_version,
        selected_strand=strand,
        expected_grade_band_entry_skill=placement.skill_code,
        expected_entry_label=placement.entry_label,
        placement_mode=mode,
        evidence_sparse=placement.sparse_evidence,
        reason_codes=list(placement.reason_codes),
    )


def _scheduler_trace(plan: InstructionPlan) -> SchedulerTrace | None:
    if not plan.scheduler_version or not plan.scheduled_goal_code:
        return None
    return SchedulerTrace(
        selected_goal=plan.scheduled_goal_code,
        selected_strand=plan.scheduled_goal_code,
        reason_codes=list(plan.scheduler_reason_codes),
        urgency_class=plan.urgency_class or "",
        recent_goal_history=list(plan.recent_goal_history),
        deferred_goals=list(plan.deferred_goals),
        review_due=plan.review_due,
        starvation_guard_triggered=plan.starvation_guard_triggered,
        scheduler_version=plan.scheduler_version,
        why_selected=plan.scheduler_why_selected or "",
        why_deferred=list(plan.scheduler_why_deferred),
    )


def _prior_evidence(
    data: PlannerInput, plan: InstructionPlan
) -> list[PriorEvidenceTrace]:
    codes = [plan.primary_skill_code, *prerequisites_for(plan.primary_skill_code)]
    if plan.supporting_skill_code:
        codes.append(plan.supporting_skill_code)
    seen: set[str] = set()
    rows: list[PriorEvidenceTrace] = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        state = data.states.get(code)
        academic = state.academic if state else None
        band = academic.band if academic else AcademicBand.NOT_OBSERVED
        prereqs = prerequisites_for(code)
        sufficient = all(_prereq_ok(data, item) for item in prereqs)
        rows.append(
            PriorEvidenceTrace(
                skill_code=code,
                parent_friendly_name=display_name(code),
                band=band.value,
                needs_remediation=bool(academic.needs_remediation)
                if academic
                else False,
                usable_evidence_count=academic.usable_evidence_count if academic else 0,
                distinct_session_count=academic.distinct_session_count
                if academic
                else 0,
                most_recent_result=None,
                most_recent_independent_result=(
                    "correct_independently"
                    if academic and academic.last_independent_success_at
                    else None
                ),
                last_practiced_date=_date_label(
                    academic.last_practiced_at.isoformat()
                    if academic and academic.last_practiced_at
                    else None
                ),
                last_independent_success=_date_label(
                    academic.last_independent_success_at.isoformat()
                    if academic and academic.last_independent_success_at
                    else None
                ),
                prerequisite_state_sufficient=sufficient,
            )
        )
    return rows


def _prereq_ok(data: PlannerInput, code: str) -> bool:
    state = data.states.get(code)
    if state is None or state.academic is None:
        return True
    return (
        state.academic.band not in {AcademicBand.EMERGING}
        or not state.academic.needs_remediation
    )


def _curriculum_trace(
    plan: InstructionPlan, data: PlannerInput
) -> CurriculumDecisionTrace:
    catalog = definition_by_code()
    definition = catalog.get(plan.primary_skill_code) or {}
    chain = list(prerequisites_for(plan.primary_skill_code))
    status = []
    for code in chain:
        state = data.states.get(code)
        band = (
            state.academic.band.value
            if state and state.academic
            else AcademicBand.NOT_OBSERVED.value
        )
        status.append(f"{code}:{band}")
    grade = None
    if definition.get("grade_band_min") is not None:
        grade = f"{definition.get('grade_band_min')}-{definition.get('grade_band_max')}"
    return CurriculumDecisionTrace(
        target_skill=plan.primary_skill_code,
        parent_friendly_skill_name=display_name(plan.primary_skill_code),
        prerequisite_chain=chain,
        prerequisite_status=status,
        grade_band=grade,
        standard_reference=_STANDARD.get(plan.primary_skill_code),
    )


def _preparation_trace(session: Session, child: Child) -> NextWinPreparationTrace:
    from daily_win_api.domains.daily_wins.preparation import read_next_win_preparation

    prep = read_next_win_preparation(session, child)
    return NextWinPreparationTrace(
        status=prep.status,
        trigger=prep.trigger,
        generated_after_reflection=prep.generated_after_reflection,
        attempt_count=prep.attempt_count,
        error_code=prep.error_code,
        model=prep.model,
        prompt_version=prep.prompt_version,
        latency_ms=prep.latency_ms,
        plan_valid=prep.plan_valid,
    )


def _coach_trace(plan: InstructionPlan) -> CoachProtocolTrace | None:
    payload = plan.coach_protocol if isinstance(plan.coach_protocol, dict) else None
    if not payload:
        return None
    return CoachProtocolTrace(
        protocol_version=str(payload.get("protocol_version") or COACH_PROTOCOL_V1),
        expected_challenge=str(payload.get("expected_challenge_level") or ""),
        initial_parent_behavior=str(payload.get("initial_wait_behavior") or ""),
        prompt_ceiling=str(payload.get("prompt_ceiling") or ""),
        frustration_response=str(payload.get("frustration_response") or ""),
        assessment_boundary=str(payload.get("assessment_boundary") or ""),
        coach_card=[str(item) for item in (payload.get("coach_card") or [])],
        teach_the_coach=bool(payload.get("teach_the_coach")),
    )


def _weekly_trace(plan: InstructionPlan) -> WeeklyContextTrace | None:
    if not plan.scheduler_version and not plan.discovery_cycle:
        return None
    return WeeklyContextTrace(
        summary_version="weekly_summary_v1",
        wins_this_week=0,
        academic_areas=[],
        next_week_focus=plan.scheduled_goal_code,
    )


def _plan_trace(plan: InstructionPlan) -> InstructionPlanTrace:
    return InstructionPlanTrace(
        primary_skill=plan.primary_skill_code,
        supporting_skill=plan.supporting_skill_code,
        mode=plan.instruction_mode.value,
        difficulty=plan.intended_difficulty,
        scaffold=plan.scaffold_level.value,
        growth_overlay=plan.growth_target_code,
        duration_minutes=plan.duration_minutes,
        reason_codes=list(plan.selection_reason_codes),
        policy_version=plan.policy_version,
        recent_themes_excluded=list(plan.recent_themes_to_avoid),
        assessment_objective=plan.assessment_objective,
    )


def _assessment_trace(plan: InstructionPlan) -> AssessmentPlanTrace:
    probe = plan.assessment_probe or {}
    mode = plan.instruction_mode.value
    kind = "practice"
    if mode == "diagnostic":
        kind = "diagnostic"
    elif mode == "review":
        kind = "review"
    elif mode == "remediation":
        kind = "remediation"
    elif mode in {"introduce", "foundation_review"}:
        kind = (
            "diagnostic"
            if mode == "introduce" and "diagnostic_check" in plan.selection_reason_codes
            else mode
        )
    contracts = contracts_for_plan(plan)
    return AssessmentPlanTrace(
        canonical_probe=str(probe.get("observable_task") or ""),
        expected_outcome=str(probe.get("expected_outcome") or ""),
        success_criterion=str(probe.get("success_criteria") or ""),
        allowed_support=str(probe.get("allowed_support") or ""),
        counts_apply=bool(probe.get("count_guidance")),
        fresh_item_rule_applies=FRESH_ASSESSMENT_ITEM in contracts,
        probe_kind=kind,
    )


def _renderer_trace(
    run: AiRun | None, plan: InstructionPlan, win: DailyWin | None
) -> tuple[RendererTrace, GenerationFailureTrace | None]:
    contracts = list(contracts_for_plan(plan))
    manifest = (
        run.context_manifest if run and isinstance(run.context_manifest, dict) else {}
    )
    failure_blob = (
        manifest.get("generation_failure")
        if isinstance(manifest.get("generation_failure"), dict)
        else {}
    )
    attempt_count = int(
        failure_blob.get("attempt_count")
        or manifest.get("generation_attempt_count")
        or 1
    )
    failed_contracts = [
        str(item) for item in (failure_blob.get("failed_contracts") or [])
    ]
    safety_rule = failure_blob.get("safety_rule")
    api_code = run.error_code if run else None
    trace_code = trace_failure_code(api_code)
    validation = "passed" if win is not None else "not_run"
    safety = "passed" if win is not None else "not_run"
    failure = None
    if trace_code:
        validation = "failed"
        if trace_code == "unsafe_content":
            safety = "failed"
        failure = GenerationFailureTrace(
            reason_code=trace_code,
            failed_contract_ids=failed_contracts,
            safety_rule=str(safety_rule) if safety_rule else None,
            parent_safe_summary=failure_summary(trace_code),
        )
    renderer = RendererTrace(
        prompt_version=(run.prompt_version if run else PROMPT_VERSION),
        model=(run.model if run and run.model != "pending" else DEFAULT_OPENAI_MODEL),
        schema_version=f"in{INPUT_SCHEMA_VERSION}/out{OUTPUT_SCHEMA_VERSION}",
        required_renderer_contracts=contracts,
        generation_attempt_count=attempt_count,
        validation_result=validation,
        contract_failures=failed_contracts,
        safety_result=safety,
        safety_rule=str(safety_rule) if safety_rule else None,
    )
    return renderer, failure


def _reflection_trace(feedback: DailyWinFeedback | None) -> ReflectionTrace | None:
    if feedback is None:
        return None
    return ReflectionTrace(
        academic_result=feedback.academic_result,
        correct_count=feedback.correct_count,
        attempted_count=feedback.attempted_count,
        persistence_observation=feedback.setback_response,
        difficulty=feedback.difficulty,
        engagement=feedback.engagement,
        completion=feedback.completion,
    )


def _state_deltas(
    plan: InstructionPlan,
    before: dict[str, PlannerSkillState],
    after: dict[str, PlannerSkillState],
    evidence_result: str | None,
) -> list[SkillStateDelta]:
    codes = {plan.primary_skill_code, PERSISTENCE_SKILL_CODE}
    if plan.supporting_skill_code:
        codes.add(plan.supporting_skill_code)
    deltas: list[SkillStateDelta] = []
    for code in sorted(codes):
        before_state = before.get(code)
        after_state = after.get(code)
        before_band = (
            before_state.academic.band.value
            if before_state and before_state.academic
            else AcademicBand.NOT_OBSERVED.value
        )
        after_band = (
            after_state.academic.band.value
            if after_state and after_state.academic
            else before_band
        )
        if code == PERSISTENCE_SKILL_CODE:
            before_band = (
                (before_state.latest_growth_signal or "not_observed")
                if before_state
                else "not_observed"
            )
            after_band = (
                (after_state.latest_growth_signal or before_band)
                if after_state
                else before_band
            )
        before_sessions = (
            before_state.academic.distinct_session_count
            if before_state and before_state.academic
            else 0
        )
        after_sessions = (
            after_state.academic.distinct_session_count
            if after_state and after_state.academic
            else before_sessions
        )
        deltas.append(
            SkillStateDelta(
                skill_code=code,
                parent_friendly_name=display_name(code),
                before_band=before_band,
                after_band=str(after_band),
                before_sessions=before_sessions,
                after_sessions=after_sessions,
                before_needs_remediation=bool(
                    before_state.academic.needs_remediation
                    if before_state and before_state.academic
                    else False
                ),
                after_needs_remediation=bool(
                    after_state.academic.needs_remediation
                    if after_state and after_state.academic
                    else False
                ),
                evidence_result=evidence_result
                if code == plan.primary_skill_code
                else None,
            )
        )
    return deltas


def _planner_input_as_of(
    session: Session, child: Child, as_of: datetime
) -> PlannerInput:
    baseline = session.scalars(
        select(ChildBaseline)
        .where(
            ChildBaseline.child_id == child.id,
            ChildBaseline.household_id == child.household_id,
            ChildBaseline.recorded_at <= as_of,
        )
        .order_by(ChildBaseline.recorded_at.desc())
        .limit(1)
    ).first()
    if baseline is None:
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
    events = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
            LearningEvent.occurred_at <= as_of,
        )
        .order_by(LearningEvent.occurred_at.asc())
    ).all()
    states = _states_from_events(session, events, as_of)
    wins = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
            DailyWin.created_at < as_of,
        )
        .order_by(DailyWin.created_at.desc())
        .limit(RECENT_DAILY_WINS_CAP)
    ).all()
    skill_ids = [win.primary_skill_id for win in wins]
    skills = (
        {
            skill.id: skill
            for skill in session.scalars(select(Skill).where(Skill.id.in_(skill_ids)))
        }
        if skill_ids
        else {}
    )
    history = load_recent_instruction_history(session, child, before=as_of)
    return PlannerInput(
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
        recent_skill_codes=history[0]
        or tuple(
            skills[win.primary_skill_id].code
            for win in wins
            if win.primary_skill_id in skills
        ),
        recent_themes=tuple(win.title for win in wins[:3]),
        now=as_of,
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


def _states_from_events(
    session: Session, events: list[LearningEvent], now: datetime
) -> dict[str, PlannerSkillState]:
    skill_ids = {event.skill_id for event in events if event.skill_id is not None}
    skills = (
        {
            skill.id: skill
            for skill in session.scalars(select(Skill).where(Skill.id.in_(skill_ids)))
        }
        if skill_ids
        else {}
    )
    academic_by_code: dict[str, list[AcademicEvidence]] = {}
    growth: dict[str, str] = {}
    for event in events:
        skill = skills.get(event.skill_id) if event.skill_id is not None else None
        if skill is None:
            continue
        payload = event.payload if isinstance(event.payload, dict) else {}
        if event.event_type == EVENT_TYPE_SKILL_ASSESSMENT and is_academic_code(
            skill.code
        ):
            result_raw = payload.get("result")
            try:
                result = AcademicResult(str(result_raw))
            except ValueError:
                continue
            academic_by_code.setdefault(skill.code, []).append(
                AcademicEvidence(
                    event_id=None,
                    occurred_at=event.occurred_at,
                    result=result,
                    session_key=str(payload.get("session_key") or event.id),
                    correct_count=payload.get("correct_count")
                    if isinstance(payload.get("correct_count"), int)
                    else None,
                    attempted_count=payload.get("attempted_count")
                    if isinstance(payload.get("attempted_count"), int)
                    else None,
                )
            )
        if is_growth_or_life_code(skill.code) and payload.get("signal"):
            growth[skill.code] = str(payload["signal"])
    states: dict[str, PlannerSkillState] = {}
    for code, evidence in academic_by_code.items():
        snapshot = project_academic_band(evidence, now=now)
        states[code] = PlannerSkillState(
            skill_code=code,
            academic=snapshot,
            latest_growth_signal=growth.get(code),
        )
    for code, signal in growth.items():
        if code not in states:
            states[code] = PlannerSkillState(
                skill_code=code,
                academic=None,
                latest_growth_signal=signal,
            )
    return states


def _current_academic_states(
    session: Session, child: Child
) -> dict[str, AcademicStateSnapshot]:
    rows = session.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.household_id == child.household_id,
        )
    ).all()
    out: dict[str, AcademicStateSnapshot] = {}
    for state, skill in rows:
        if not is_academic_code(skill.code):
            continue
        payload = state.state if isinstance(state.state, dict) else {}
        band_raw = payload.get("band") or AcademicBand.NOT_OBSERVED.value
        try:
            band = AcademicBand(str(band_raw))
        except ValueError:
            band = AcademicBand.NOT_OBSERVED
        out[skill.code] = AcademicStateSnapshot(
            band=band,
            algorithm_version=state.algorithm_version,
            usable_evidence_count=int(payload.get("usable_evidence_count") or 0),
            distinct_session_count=int(payload.get("distinct_session_count") or 0),
            last_practiced_at=None,
            last_independent_success_at=None,
            evidence_ids=(),
            summary=str(payload.get("summary") or ""),
            needs_remediation=bool(payload.get("needs_remediation")),
        )
    return out


def _latest_win(session: Session, child: Child) -> DailyWin | None:
    return session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(1)
    ).first()


def _feedback_for(session: Session, daily_win_id: UUID) -> DailyWinFeedback | None:
    return session.scalar(
        select(DailyWinFeedback).where(DailyWinFeedback.daily_win_id == daily_win_id)
    )


def _latest_result_label(session: Session, child: Child, skill_id: UUID) -> str | None:
    event = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
            LearningEvent.skill_id == skill_id,
            LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
        )
        .order_by(LearningEvent.occurred_at.desc())
        .limit(1)
    ).first()
    if event is None or not isinstance(event.payload, dict):
        return None
    result = event.payload.get("result")
    return str(result) if result else None


def _primary_academic_goal(data: PlannerInput) -> str:
    for goal in sorted(data.goals, key=lambda item: item.priority):
        if is_academic_code(goal.skill_code):
            return goal.skill_code
    return data.goals[0].skill_code


def _date_label(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:10]


def _redact_value(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered == "id" or lowered.endswith("_id") or lowered.endswith("_ids"):
                continue
            redacted[str(key)] = _redact_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, UUID):
        return "[redacted]"
    if isinstance(value, str) and _UUID.fullmatch(value):
        return "[redacted]"
    return value
