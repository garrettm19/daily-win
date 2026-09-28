"""Frozen synthetic InstructionPlans for the Terra vs Luna renderer bakeoff."""

from dataclasses import dataclass

from daily_win_api.ai.schemas import (
    DailyWinModelContext,
    EvidenceSummaryContext,
    InstructionPlanContext,
    Material,
    ParentReportedBaselineContext,
)
from daily_win_api.domains.daily_wins.context import instruction_plan_context
from daily_win_api.domains.learning.planner import InstructionPlan, plan_instruction
from daily_win_api.eval.planner_cases import PlannerCase, planner_golden_cases

ALLOWED_MATERIALS = [item.value for item in Material]

# Coverage ids are bakeoff labels. Golden planner cases supply the frozen plans.
_SPECS: tuple[tuple[str, str, str], ...] = (
    ("case_1_age5_math_intro", "age 5 math introduction", "math_counting_new"),
    ("case_2_age6_phonics", "age 6 reading/phonics", "reading_cvc_unlocked"),
    (
        "case_3_age7_writing_org",
        "age 7 writing organization",
        "writing_org_missing_sentence",
    ),
    (
        "case_4_age8_diagnostic_math",
        "age 8 diagnostic math",
        "growth_overlay_does_not_steal_skill",
    ),
    (
        "case_5_age9_comprehension",
        "age 9 reading comprehension",
        "reading_inference_unlocked",
    ),
    (
        "case_6_remediation",
        "remediation case",
        "emerging_plus_flag_is_remediation",
    ),
    ("case_7_review_retained", "review/retained case", "math_review_spacing"),
    (
        "case_8_growth_overlay",
        "growth overlay + academic target",
        "growth_overlay_does_not_steal_skill",
    ),
)


@dataclass(frozen=True)
class BakeoffCase:
    id: str
    coverage: str
    golden_id: str
    profile_summary: str
    plan_summary: str
    plan: InstructionPlan
    context: DailyWinModelContext
    context_sha256: str


def load_bakeoff_cases() -> tuple[BakeoffCase, ...]:
    goldens = {item.id: item for item in planner_golden_cases()}
    cases: list[BakeoffCase] = []
    for case_id, coverage, golden_id in _SPECS:
        golden = goldens[golden_id]
        plan = plan_instruction(golden.data)
        context = _frozen_context(golden, plan)
        cases.append(
            BakeoffCase(
                id=case_id,
                coverage=coverage,
                golden_id=golden_id,
                profile_summary=_profile_summary(golden),
                plan_summary=_plan_summary(plan),
                plan=plan,
                context=context,
                context_sha256=_sha256(context.model_dump_json()),
            )
        )
    return tuple(cases)


def _frozen_context(golden: PlannerCase, plan: InstructionPlan) -> DailyWinModelContext:
    data = golden.data
    return DailyWinModelContext(
        nickname=data.nickname,
        parent_reported_baseline=ParentReportedBaselineContext(
            age_years=data.age_years,
            grade=data.grade,
            interests=list(data.interests),
            strengths=["curious"],
            current_difficulties=[],
            motivators=list(data.motivators),
            response_to_difficulty=None,
            preferred_activity_minutes=data.preferred_duration_minutes,
        ),
        instruction_plan=_plan_context(plan),
        bounded_evidence_summaries=_synthetic_evidence(golden),
        recent_themes=list(data.recent_themes)[:3],
        allowed_skill_codes=_allowed_from_plan(plan),
        allowed_materials=list(ALLOWED_MATERIALS),
    )


def _plan_context(plan: InstructionPlan) -> InstructionPlanContext:
    return instruction_plan_context(plan)


def _allowed_from_plan(plan: InstructionPlan) -> list[str]:
    codes = [plan.primary_skill_code]
    for extra in (plan.supporting_skill_code, plan.growth_target_code):
        if extra and extra not in codes:
            codes.append(extra)
    return codes


def _synthetic_evidence(golden: PlannerCase) -> list[EvidenceSummaryContext]:
    rows: list[EvidenceSummaryContext] = []
    for code, item in golden.data.states.items():
        if item.academic is not None:
            rows.append(
                EvidenceSummaryContext(
                    skill_code=code,
                    summary=(
                        "Synthetic parent observation: last independent try on "
                        f"{code} looked {item.academic.band.value}."
                    ),
                    reporting_kind="parent_observation",
                )
            )
        if item.latest_growth_signal:
            readable = item.latest_growth_signal.replace("_", " ")
            rows.append(
                EvidenceSummaryContext(
                    skill_code=code,
                    summary=(
                        "Synthetic parent observation: after a stall, the child "
                        f"showed {readable}."
                    ),
                    reporting_kind="parent_observation",
                )
            )
    return rows[:6]


def _profile_summary(golden: PlannerCase) -> str:
    data = golden.data
    interests = ", ".join(data.interests) or "none listed"
    return (
        f"{data.nickname}, age {data.age_years}, grade {data.grade}. "
        f"Interests: {interests}. Synthetic eval profile only."
    )


def _plan_summary(plan: InstructionPlan) -> str:
    probe = plan.assessment_probe if isinstance(plan.assessment_probe, dict) else {}
    task = str(probe.get("observable_task") or plan.assessment_objective)
    growth = plan.growth_target_code or "none"
    return (
        f"primary={plan.primary_skill_code}; mode={plan.instruction_mode.value}; "
        f"difficulty={plan.intended_difficulty}; "
        f"scaffold={plan.scaffold_level.value}; "
        f"duration={plan.duration_minutes} min; growth={growth}; "
        f"probe={task}"
    )


def _sha256(payload: str) -> str:
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
