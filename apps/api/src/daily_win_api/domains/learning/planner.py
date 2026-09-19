from dataclasses import dataclass
from datetime import datetime

from daily_win_api.domains.daily_wins.adaptation import build_adaptation_directive
from daily_win_api.domains.learning.academic import (
    AcademicStateSnapshot,
    due_for_review,
)
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    InstructionMode,
    ScaffoldLevel,
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
INSTRUCTION_POLICY_CURRENT = INSTRUCTION_POLICY_V2
DIAGNOSTIC_MIN_AGE = 8


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


def plan_instruction(data: PlannerInput) -> InstructionPlan:
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
    parent_priority_code = (
        academic_goal.skill_code
        if academic_goal is not None
        else data.goals[0].skill_code
    )
    candidates = _expand_candidates(parent_priority_code, data.age_years, catalog)
    chosen, reasons, mode, prereq_note = _choose_skill(candidates, data)
    definition = catalog[chosen]
    academic_state = data.states.get(chosen)
    band = (
        academic_state.academic.band
        if academic_state and academic_state.academic
        else AcademicBand.NOT_OBSERVED
    )
    scaffold = _scaffold_for(band, mode)
    difficulty = _difficulty_for(band, mode)
    supporting = _supporting_skill(chosen, candidates, data, growth_goal)
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
    probe = probe_for_skill(chosen)
    outcome = definition.get("measurable_outcome") or definition["display_name"]
    minutes = max(10, min(25, data.preferred_duration_minutes))
    return InstructionPlan(
        primary_skill_code=chosen,
        supporting_skill_code=supporting,
        selection_reason_codes=reasons,
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
        policy_version=INSTRUCTION_POLICY_CURRENT,
        academic_band=band.value,
    )


def _expand_candidates(
    parent_code: str, age_years: int, catalog: dict[str, dict[str, object]]
) -> list[str]:
    children = [
        str(item["code"])
        for item in child_skills_for_parent(parent_code)
        if is_generation_supported(str(item["code"]))
    ]
    del age_years
    if children:
        return children
    if parent_code in catalog and is_generation_supported(parent_code):
        return [parent_code]
    return ["math.number_sense.counting"]


def _choose_skill(
    candidates: list[str], data: PlannerInput
) -> tuple[str, tuple[str, ...], InstructionMode, str]:
    reasons: list[str] = ["parent_priority", "age_grade_appropriate"]
    for code in candidates:
        missing = _missing_prereq(code, data)
        if missing is not None:
            missing_state = data.states.get(missing)
            missing_snapshot = missing_state.academic if missing_state else None
            missing_band = (
                missing_snapshot.band if missing_snapshot else AcademicBand.NOT_OBSERVED
            )
            mode = _mode_for(missing, missing_band, missing_snapshot, data)
            if mode is InstructionMode.REMEDIATION:
                reasons.append("regression_review")
            else:
                reasons.append("prerequisite_evidence_missing")
            if mode is InstructionMode.DIAGNOSTIC:
                reasons.append("diagnostic_check")
            return (
                missing,
                tuple(reasons),
                mode,
                f"Review {missing} before {code}.",
            )
        state = data.states.get(code)
        snapshot = state.academic if state else None
        band = snapshot.band if snapshot else AcademicBand.NOT_OBSERVED
        if _recent_regression(snapshot):
            reasons.append("regression_review")
            return (
                code,
                tuple(reasons),
                InstructionMode.REMEDIATION,
                "Later evidence warrants review.",
            )
        if snapshot is not None and due_for_review(snapshot, now=data.now):
            reasons.append("review_spacing")
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


def _missing_prereq(code: str, data: PlannerInput) -> str | None:
    for prereq in prerequisites_for(code):
        deeper = _missing_prereq(prereq, data)
        if deeper is not None:
            return deeper
        if _band_for(prereq, data) not in {
            AcademicBand.DEMONSTRATED,
            AcademicBand.RETAINED,
        }:
            return prereq
    return None


def _band_for(code: str, data: PlannerInput) -> AcademicBand:
    state = data.states.get(code)
    if state and state.academic:
        return state.academic.band
    return AcademicBand.NOT_OBSERVED


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
) -> str | None:
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
    return _missing_prereq(code, data) is None
