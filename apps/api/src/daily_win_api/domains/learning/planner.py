from dataclasses import dataclass
from datetime import datetime

from daily_win_api.domains.daily_wins.adaptation import build_adaptation_directive
from daily_win_api.domains.learning.academic import (
    AcademicStateSnapshot,
    due_for_review,
)
from daily_win_api.domains.learning.bonus import choose_bonus
from daily_win_api.domains.learning.coach_protocol import build_coach_protocol
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    InstructionMode,
    ScaffoldLevel,
)
from daily_win_api.domains.learning.placement import (
    PLACEMENT_POLICY_CURRENT,
    decide_placement,
    direct_step_down,
    is_unknown,
    observed_weak,
    placement_probe,
    presentation_constraint_for,
    remap_generation_goal,
    should_step_down,
)
from daily_win_api.domains.learning.prerequisites import prerequisites_for
from daily_win_api.domains.learning.probes import probe_for_skill
from daily_win_api.domains.learning.taxonomy import (
    child_skills_for_parent,
    definition_by_code,
    is_academic_code,
    is_generation_supported,
    is_growth_or_life_code,
)

INSTRUCTION_POLICY_V1 = "instruction_policy_v1"
INSTRUCTION_POLICY_V2 = "instruction_policy_v2"
INSTRUCTION_POLICY_V3 = "instruction_policy_v3"
INSTRUCTION_POLICY_V4 = "instruction_policy_v4"
INSTRUCTION_POLICY_CURRENT = INSTRUCTION_POLICY_V4
DIAGNOSTIC_MIN_AGE = 8
SPARSE_DIAGNOSTIC_MIN_AGE = 7


@dataclass(frozen=True)
class GoalPriority:
    skill_code: str
    priority: int


@dataclass(frozen=True)
class PlannerSkillState:
    skill_code: str
    academic: AcademicStateSnapshot | None
    latest_growth_signal: str | None = None


@dataclass(frozen=True)
class PlannerInput:
    nickname: str
    age_years: int
    grade: str
    interests: tuple[str, ...]
    motivators: tuple[str, ...]
    preferred_duration_minutes: int
    goals: tuple[GoalPriority, ...]
    states: dict[str, PlannerSkillState]
    recent_skill_codes: tuple[str, ...]
    recent_themes: tuple[str, ...]
    now: datetime
    recent_instruction_modes: tuple[str, ...] = ()
    recent_goal_codes: tuple[str, ...] = ()
    low_engagement_categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstructionPlan:
    primary_skill_code: str
    supporting_skill_code: str | None
    selection_reason_codes: tuple[str, ...]
    instruction_mode: InstructionMode
    intended_difficulty: str
    scaffold_level: ScaffoldLevel
    prerequisite_rationale: str
    assessment_objective: str
    assessment_probe: dict[str, object]
    desired_evidence: str
    growth_target_code: str | None
    growth_adaptation_summary: str | None
    duration_minutes: int
    engagement_theme_constraints: tuple[str, ...]
    recent_themes_to_avoid: tuple[str, ...]
    policy_version: str
    academic_band: str | None
    placement_policy_version: str = PLACEMENT_POLICY_CURRENT
    placement_entry_label: str = ""
    placement_why: str = ""
    presentation_constraint: str | None = None
    scheduler_version: str | None = None
    scheduled_goal_code: str | None = None
    scheduler_reason_codes: tuple[str, ...] = ()
    urgency_class: str | None = None
    deferred_goals: tuple[str, ...] = ()
    starvation_guard_triggered: bool = False
    review_due: bool = False
    application_variant: str | None = None
    scheduler_why_selected: str | None = None
    scheduler_why_deferred: tuple[str, ...] = ()
    recent_goal_history: tuple[str, ...] = ()
    coach_protocol: dict[str, object] | None = None
    discovery_cycle: bool = False
    bonus_challenge: dict[str, object] | None = None
    teach_the_coach: bool = False


def plan_instruction(data: PlannerInput) -> InstructionPlan:
    from daily_win_api.domains.daily_wins.latency import span
    from daily_win_api.domains.learning.scheduler import schedule_instruction

    with span("scheduler"):
        focus = schedule_instruction(data)
    with span("planner"):
        return _plan_core(data, policy_version=INSTRUCTION_POLICY_V4, focus=focus)


def plan_instruction_v3(data: PlannerInput) -> InstructionPlan:
    """Frozen scheduler-less policy. Historical fixtures only."""
    return _plan_core(data, policy_version=INSTRUCTION_POLICY_V3, focus=None)


def _plan_core(data: PlannerInput, *, policy_version: str, focus) -> InstructionPlan:
    catalog = definition_by_code()
    academic_goal = next(
        (
            goal
            for goal in sorted(data.goals, key=lambda item: item.priority)
            if is_academic_code(goal.skill_code)
        ),
        None,
    )
    growth_goal = next(
        (
            goal
            for goal in sorted(data.goals, key=lambda item: item.priority)
            if is_growth_or_life_code(goal.skill_code)
        ),
        None,
    )
    if focus is not None:
        parent_priority_code = focus.selected_goal_code
        allow_review = focus.allows_review
    else:
        parent_priority_code = (
            academic_goal.skill_code
            if academic_goal is not None
            else data.goals[0].skill_code
        )
        allow_review = True
    goal_code = remap_generation_goal(parent_priority_code)
    placement = decide_placement(goal_code, data.age_years, data.states)
    candidates = _expand_candidates(goal_code, data.age_years, catalog)
    if placement.sparse_evidence and is_academic_code(goal_code):
        weak = _observed_weak_prereq(placement.skill_code, data)
        if weak is not None:
            chosen, reasons, mode, prereq_note = _choose_skill(
                [weak],
                data,
                allow_review=allow_review,
                policy_version=policy_version,
            )
            reason_list = list(reasons)
            if "prerequisite_evidence_missing" not in reason_list:
                reason_list.append("prerequisite_evidence_missing")
            reasons = reason_list
            probe = probe_for_skill(chosen)
        else:
            chosen = placement.skill_code
            reasons = [
                "parent_priority",
                "age_grade_appropriate",
                *placement.reason_codes,
            ]
            mode = (
                InstructionMode.DIAGNOSTIC
                if data.age_years >= SPARSE_DIAGNOSTIC_MIN_AGE
                else InstructionMode.INTRODUCE
            )
            if mode is InstructionMode.DIAGNOSTIC:
                reasons.append("diagnostic_check")
            else:
                reasons.append("insufficient_independent_evidence")
            prereq_note = placement.why
            probe = placement_probe(
                chosen, sparse_diagnostic=True, age_years=data.age_years
            )
    else:
        chosen, reasons, mode, prereq_note = _choose_skill(
            candidates,
            data,
            allow_review=allow_review,
            policy_version=policy_version,
        )
        probe = probe_for_skill(chosen)
    definition = catalog[chosen]
    academic_state = data.states.get(chosen)
    band = (
        academic_state.academic.band
        if academic_state and academic_state.academic
        else AcademicBand.NOT_OBSERVED
    )
    scaffold = _scaffold_for(band, mode)
    difficulty = _difficulty_for(band, mode)
    supporting = _supporting_skill(
        chosen, candidates, data, growth_goal, sparse=placement.sparse_evidence
    )
    growth_code = growth_goal.skill_code if growth_goal is not None else None
    growth_signal = None
    if growth_code and growth_code in data.states:
        growth_signal = data.states[growth_code].latest_growth_signal
    adaptation = None
    if growth_code:
        adaptation = build_adaptation_directive(
            skill_code=growth_code,
            latest_signal=growth_signal,
            nickname=data.nickname,
        )
    outcome = definition.get("measurable_outcome") or definition["display_name"]
    minutes = max(10, min(25, data.preferred_duration_minutes))
    constraint = presentation_constraint_for(chosen, data.age_years)
    why = prereq_note
    if placement.sparse_evidence:
        why = placement.why
    variant = (
        "transfer"
        if "terminal_transfer_review" in reasons
        or "terminal_maintenance_transfer" in reasons
        else None
    )
    protocol = None
    bonus = None
    teach = False
    if policy_version != INSTRUCTION_POLICY_V3:
        from daily_win_api.domains.daily_wins.latency import span

        with span("coach_protocol"):
            protocol_obj = build_coach_protocol(
                instruction_mode=mode,
                scaffold=scaffold,
                age_years=data.age_years,
                skill_code=chosen,
                academic_band=band.value,
                growth_target_code=growth_code,
            )
        protocol = protocol_obj.as_dict()
        teach = protocol_obj.teach_the_coach
        bonus_obj = choose_bonus(
            primary_skill_code=chosen,
            teach_the_coach=teach,
            low_engagement_categories=data.low_engagement_categories,
            age_years=data.age_years,
        )
        bonus = {
            "code": bonus_obj.code,
            "category": bonus_obj.category,
            "title": bonus_obj.title,
            "minutes": bonus_obj.minutes,
            "prompt": bonus_obj.prompt,
            "safety": bonus_obj.safety,
            "personal_best": bonus_obj.personal_best,
            "optional": bonus_obj.optional,
            "counts_as_mastery": bonus_obj.counts_as_mastery,
        }
    discovery = False if focus is None else bool(focus.discovery_cycle)
    return InstructionPlan(
        primary_skill_code=chosen,
        supporting_skill_code=supporting,
        selection_reason_codes=tuple(reasons),
        instruction_mode=mode,
        intended_difficulty=difficulty,
        scaffold_level=scaffold,
        prerequisite_rationale=prereq_note,
        assessment_objective=str(outcome),
        assessment_probe=probe,
        desired_evidence="structured academic result plus parent observation",
        growth_target_code=growth_code,
        growth_adaptation_summary=(
            adaptation.parent_facing_summary if adaptation is not None else None
        ),
        duration_minutes=minutes,
        engagement_theme_constraints=data.interests[:2],
        recent_themes_to_avoid=data.recent_themes[:3],
        policy_version=policy_version,
        academic_band=band.value,
        placement_policy_version=placement.policy_version,
        placement_entry_label=placement.entry_label,
        placement_why=why,
        presentation_constraint=constraint,
        scheduler_version=None if focus is None else focus.scheduler_version,
        scheduled_goal_code=None if focus is None else focus.selected_goal_code,
        scheduler_reason_codes=() if focus is None else focus.selection_reason_codes,
        urgency_class=None if focus is None else focus.urgency_class,
        deferred_goals=() if focus is None else focus.deferred_goals,
        starvation_guard_triggered=(
            False if focus is None else focus.starvation_guard_triggered
        ),
        review_due=False if focus is None else focus.review_due,
        application_variant=variant,
        scheduler_why_selected=None if focus is None else focus.why_selected,
        scheduler_why_deferred=() if focus is None else focus.why_deferred,
        recent_goal_history=() if focus is None else focus.recent_goal_history,
        coach_protocol=protocol,
        discovery_cycle=discovery,
        bonus_challenge=bonus,
        teach_the_coach=teach,
    )


def _expand_candidates(
    parent_code: str, age_years: int, catalog: dict[str, dict[str, object]]
) -> list[str]:
    del age_years
    code = remap_generation_goal(parent_code)
    children = [
        str(item["code"])
        for item in child_skills_for_parent(code)
        if is_generation_supported(str(item["code"]))
    ]
    if children:
        return children
    if code in catalog and is_generation_supported(code):
        return [code]
    return ["math.number_sense.counting"]


def _choose_skill(
    candidates: list[str],
    data: PlannerInput,
    *,
    allow_review: bool = True,
    policy_version: str = INSTRUCTION_POLICY_V4,
) -> tuple[str, tuple[str, ...], InstructionMode, str]:
    reasons: list[str] = ["parent_priority", "age_grade_appropriate"]
    from daily_win_api.domains.learning.scheduler import review_cooled

    for code in reversed(candidates):
        snapshot = _snapshot(code, data)
        if _recent_regression(snapshot):
            continue
        if should_step_down(code, snapshot, data.states):
            down = direct_step_down(code)
            if down is None:
                continue
            down_snap = _snapshot(down, data)
            if _recent_regression(down_snap):
                mode = InstructionMode.REMEDIATION
                reasons.append("regression_review")
            elif observed_weak(down_snap):
                mode = InstructionMode.PRACTICE
                reasons.append("insufficient_independent_evidence")
            else:
                mode = InstructionMode.INTRODUCE
                reasons.append("foundation_review")
            reasons.append("placement_step_down")
            return (
                down,
                tuple(reasons),
                mode,
                "Recent diagnostic showed significant support was needed.",
            )
    for code in candidates:
        snapshot = _snapshot(code, data)
        band = snapshot.band if snapshot else AcademicBand.NOT_OBSERVED
        if _recent_regression(snapshot):
            reasons.append("regression_review")
            return (
                code,
                tuple(reasons),
                InstructionMode.REMEDIATION,
                "Later evidence warrants review.",
            )
        weak = _observed_weak_prereq(code, data)
        if weak is not None:
            weak_state = data.states.get(weak)
            weak_snapshot = weak_state.academic if weak_state else None
            weak_band = (
                weak_snapshot.band if weak_snapshot else AcademicBand.NOT_OBSERVED
            )
            mode = _mode_for(weak, weak_band, weak_snapshot, data)
            if mode is InstructionMode.REMEDIATION:
                reasons.append("regression_review")
            else:
                reasons.append("prerequisite_evidence_missing")
            if mode is InstructionMode.DIAGNOSTIC:
                reasons.append("diagnostic_check")
            return (
                weak,
                tuple(reasons),
                mode,
                f"Review {weak} before {code}.",
            )
        if is_unknown(snapshot) and _later_observed(code, candidates, data):
            continue
        if snapshot is not None and due_for_review(snapshot, now=data.now):
            if policy_version != INSTRUCTION_POLICY_V3:
                if not allow_review or review_cooled(code, data):
                    continue
            reasons.append("review_spacing")
            if policy_version != INSTRUCTION_POLICY_V3 and code == candidates[-1]:
                reasons.append("terminal_transfer_review")
            return (
                code,
                tuple(reasons),
                InstructionMode.REVIEW,
                "Previously demonstrated; due for review.",
            )
        if band in {
            AcademicBand.EMERGING,
            AcademicBand.NOT_OBSERVED,
            AcademicBand.DEVELOPING,
        }:
            mode = _mode_for(code, band, snapshot, data)
            if mode is InstructionMode.DIAGNOSTIC:
                reasons.append("diagnostic_check")
            else:
                reasons.append("insufficient_independent_evidence")
            return (
                code,
                tuple(reasons),
                mode,
                "Prerequisites are sufficiently evidenced or none apply.",
            )
    chosen = candidates[-1]
    snapshot = _snapshot(chosen, data)
    if (
        policy_version != INSTRUCTION_POLICY_V3
        and snapshot is not None
        and snapshot.band in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}
    ):
        reasons.append("terminal_maintenance_transfer")
        if chosen == candidates[-1]:
            reasons.append("terminal_transfer_review")
        return (
            chosen,
            tuple(reasons),
            InstructionMode.REVIEW,
            "Terminal skill is retained; ordinary practice stops.",
        )
    reasons.append("progression_next")
    return (
        chosen,
        tuple(reasons),
        InstructionMode.PRACTICE,
        "Prerequisites are sufficiently evidenced.",
    )


def _mode_for(
    code: str,
    band: AcademicBand,
    snapshot: AcademicStateSnapshot | None,
    data: PlannerInput,
) -> InstructionMode:
    if _recent_regression(snapshot):
        return InstructionMode.REMEDIATION
    if band is AcademicBand.NOT_OBSERVED:
        if is_academic_code(code) and data.age_years >= DIAGNOSTIC_MIN_AGE:
            return InstructionMode.DIAGNOSTIC
        return InstructionMode.INTRODUCE
    return InstructionMode.PRACTICE


def _observed_weak_prereq(code: str, data: PlannerInput) -> str | None:
    for prereq in prerequisites_for(code):
        deeper = _observed_weak_prereq(prereq, data)
        if deeper is not None:
            return deeper
        if observed_weak(_snapshot(prereq, data)):
            return prereq
    return None


def _later_observed(code: str, candidates: list[str], data: PlannerInput) -> bool:
    seen = False
    for item in candidates:
        if item == code:
            seen = True
            continue
        if not seen:
            continue
        if not is_unknown(_snapshot(item, data)):
            return True
    return False


def _snapshot(code: str, data: PlannerInput) -> AcademicStateSnapshot | None:
    state = data.states.get(code)
    if state and state.academic:
        return state.academic
    return None


def _recent_regression(snapshot: AcademicStateSnapshot | None) -> bool:
    return snapshot is not None and snapshot.needs_remediation


def _scaffold_for(band: AcademicBand, mode: InstructionMode) -> ScaffoldLevel:
    if mode is InstructionMode.REMEDIATION:
        return ScaffoldLevel.HIGH
    if mode is InstructionMode.DIAGNOSTIC:
        return ScaffoldLevel.MEDIUM
    if band in {AcademicBand.NOT_OBSERVED, AcademicBand.EMERGING}:
        return ScaffoldLevel.HIGH
    if band is AcademicBand.DEVELOPING or mode is InstructionMode.REVIEW:
        return ScaffoldLevel.MEDIUM
    return ScaffoldLevel.LOW


def plan_from_dict(payload: dict[str, object]) -> InstructionPlan:
    """Rebuild an InstructionPlan from persisted JSON. Not a new decision."""
    reasons = payload.get("selection_reason_codes") or []
    probe = payload.get("assessment_probe") or {}
    themes = payload.get("engagement_theme_constraints") or []
    avoid = payload.get("recent_themes_to_avoid") or []
    return InstructionPlan(
        primary_skill_code=str(payload["primary_skill_code"]),
        supporting_skill_code=(
            str(payload["supporting_skill_code"])
            if payload.get("supporting_skill_code")
            else None
        ),
        selection_reason_codes=tuple(str(item) for item in reasons),
        instruction_mode=InstructionMode(str(payload["instruction_mode"])),
        intended_difficulty=str(payload["intended_difficulty"]),
        scaffold_level=ScaffoldLevel(str(payload["scaffold_level"])),
        prerequisite_rationale=str(payload.get("prerequisite_rationale") or ""),
        assessment_objective=str(payload.get("assessment_objective") or ""),
        assessment_probe=dict(probe) if isinstance(probe, dict) else {},
        desired_evidence=str(payload.get("desired_evidence") or ""),
        growth_target_code=(
            str(payload["growth_target_code"])
            if payload.get("growth_target_code")
            else None
        ),
        growth_adaptation_summary=(
            str(payload["growth_adaptation_summary"])
            if payload.get("growth_adaptation_summary")
            else None
        ),
        duration_minutes=int(payload.get("duration_minutes") or 15),
        engagement_theme_constraints=tuple(str(item) for item in themes),
        recent_themes_to_avoid=tuple(str(item) for item in avoid),
        policy_version=str(payload.get("policy_version") or INSTRUCTION_POLICY_CURRENT),
        academic_band=(
            str(payload["academic_band"]) if payload.get("academic_band") else None
        ),
        placement_policy_version=str(
            payload.get("placement_policy_version") or PLACEMENT_POLICY_CURRENT
        ),
        placement_entry_label=str(payload.get("placement_entry_label") or ""),
        placement_why=str(payload.get("placement_why") or ""),
        presentation_constraint=(
            str(payload["presentation_constraint"])
            if payload.get("presentation_constraint")
            else None
        ),
        scheduler_version=(
            str(payload["scheduler_version"])
            if payload.get("scheduler_version")
            else None
        ),
        scheduled_goal_code=(
            str(payload["scheduled_goal_code"])
            if payload.get("scheduled_goal_code")
            else None
        ),
        scheduler_reason_codes=tuple(
            str(item) for item in (payload.get("scheduler_reason_codes") or [])
        ),
        urgency_class=(
            str(payload["urgency_class"]) if payload.get("urgency_class") else None
        ),
        deferred_goals=tuple(
            str(item) for item in (payload.get("deferred_goals") or [])
        ),
        starvation_guard_triggered=bool(
            payload.get("starvation_guard_triggered") or False
        ),
        review_due=bool(payload.get("review_due") or False),
        application_variant=(
            str(payload["application_variant"])
            if payload.get("application_variant")
            else None
        ),
        scheduler_why_selected=(
            str(payload["scheduler_why_selected"])
            if payload.get("scheduler_why_selected")
            else None
        ),
        scheduler_why_deferred=tuple(
            str(item) for item in (payload.get("scheduler_why_deferred") or [])
        ),
        recent_goal_history=tuple(
            str(item) for item in (payload.get("recent_goal_history") or [])
        ),
        coach_protocol=(
            dict(payload["coach_protocol"])
            if isinstance(payload.get("coach_protocol"), dict)
            else None
        ),
        discovery_cycle=bool(payload.get("discovery_cycle") or False),
        bonus_challenge=(
            dict(payload["bonus_challenge"])
            if isinstance(payload.get("bonus_challenge"), dict)
            else None
        ),
        teach_the_coach=bool(payload.get("teach_the_coach") or False),
    )


def plan_as_dict(plan: InstructionPlan) -> dict[str, object]:
    return {
        "primary_skill_code": plan.primary_skill_code,
        "supporting_skill_code": plan.supporting_skill_code,
        "selection_reason_codes": list(plan.selection_reason_codes),
        "instruction_mode": plan.instruction_mode.value,
        "intended_difficulty": plan.intended_difficulty,
        "scaffold_level": plan.scaffold_level.value,
        "prerequisite_rationale": plan.prerequisite_rationale,
        "assessment_objective": plan.assessment_objective,
        "assessment_probe": plan.assessment_probe,
        "desired_evidence": plan.desired_evidence,
        "growth_target_code": plan.growth_target_code,
        "growth_adaptation_summary": plan.growth_adaptation_summary,
        "duration_minutes": plan.duration_minutes,
        "engagement_theme_constraints": list(plan.engagement_theme_constraints),
        "recent_themes_to_avoid": list(plan.recent_themes_to_avoid),
        "policy_version": plan.policy_version,
        "academic_band": plan.academic_band,
        "placement_policy_version": plan.placement_policy_version,
        "placement_entry_label": plan.placement_entry_label,
        "placement_why": plan.placement_why,
        "presentation_constraint": plan.presentation_constraint,
        "scheduler_version": plan.scheduler_version,
        "scheduled_goal_code": plan.scheduled_goal_code,
        "scheduler_reason_codes": list(plan.scheduler_reason_codes),
        "urgency_class": plan.urgency_class,
        "deferred_goals": list(plan.deferred_goals),
        "starvation_guard_triggered": plan.starvation_guard_triggered,
        "review_due": plan.review_due,
        "application_variant": plan.application_variant,
        "scheduler_why_selected": plan.scheduler_why_selected,
        "scheduler_why_deferred": list(plan.scheduler_why_deferred),
        "recent_goal_history": list(plan.recent_goal_history),
        "coach_protocol": plan.coach_protocol,
        "discovery_cycle": plan.discovery_cycle,
        "bonus_challenge": plan.bonus_challenge,
        "teach_the_coach": plan.teach_the_coach,
    }


def _difficulty_for(band: AcademicBand, mode: InstructionMode) -> str:
    if mode is InstructionMode.REMEDIATION:
        return "reduce"
    if mode is InstructionMode.DIAGNOSTIC:
        return "similar"
    if band in {AcademicBand.NOT_OBSERVED, AcademicBand.EMERGING}:
        return "reduce"
    if band is AcademicBand.RETAINED:
        return "slightly_increase"
    return "similar"


def _supporting_skill(
    primary: str,
    candidates: list[str],
    data: PlannerInput,
    growth_goal: GoalPriority | None,
    *,
    sparse: bool,
) -> str | None:
    if not sparse:
        for code in candidates:
            if code == primary:
                continue
            if not _supporting_allowed(code, data):
                continue
            return code
    if growth_goal is not None and growth_goal.skill_code != primary:
        return growth_goal.skill_code
    del data
    return None


def _supporting_allowed(code: str, data: PlannerInput) -> bool:
    if is_growth_or_life_code(code):
        return True
    if not is_academic_code(code) or not is_generation_supported(code):
        return False
    snapshot = _snapshot(code, data)
    if is_unknown(snapshot) or observed_weak(snapshot):
        return False
    return _observed_weak_prereq(code, data) is None
