from dataclasses import asdict, dataclass, field
from typing import Any

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.learning.planner import InstructionPlan, plan_as_dict
from daily_win_api.domains.learning.prerequisites import prerequisites_for
from daily_win_api.domains.learning.probes import probe_for_skill
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import (
    SKILL_DEFINITIONS,
    is_academic_code,
    is_generation_supported,
)

EXPERT_SCORE_KEYS = (
    "educational_usefulness",
    "target_skill_alignment",
    "age_appropriateness",
    "scaffold_appropriateness",
    "assessment_validity",
    "parent_clarity",
    "engagement",
    "overall_quality",
)


@dataclass
class ExpertReviewRecord:
    profile_summary: str
    learner_state: dict[str, Any]
    instruction_plan: dict[str, Any]
    generated_activity: dict[str, Any] | None
    assessment_probe: dict[str, Any]
    planner_rationale: list[str]
    human_scores: dict[str, int | None] = field(
        default_factory=lambda: dict.fromkeys(EXPERT_SCORE_KEYS)
    )
    verdict: str | None = None
    note: str = (
        "Human scores are evaluation artifacts only. They are not learner data "
        "and must not be written to PostgreSQL child tables."
    )


def empty_expert_record(
    *,
    profile_summary: str,
    learner_state: dict[str, Any],
    plan: InstructionPlan,
    draft: DailyWinDraft | None = None,
) -> ExpertReviewRecord:
    return ExpertReviewRecord(
        profile_summary=profile_summary,
        learner_state=learner_state,
        instruction_plan=plan_as_dict(plan),
        generated_activity=None if draft is None else draft.model_dump(mode="json"),
        assessment_probe=dict(plan.assessment_probe),
        planner_rationale=list(plan.selection_reason_codes),
    )


def expert_record_to_dict(record: ExpertReviewRecord) -> dict[str, Any]:
    return asdict(record)


def curriculum_review_sections() -> list[dict[str, Any]]:
    """One educator-facing section per active academic skill. Not learner data."""
    from daily_win_api.eval.planner_cases import planner_golden_cases

    cases = planner_golden_cases()
    sections: list[dict[str, Any]] = []
    for item in SKILL_DEFINITIONS:
        code = str(item["code"])
        if item.get("skill_kind") != "skill" or not is_academic_code(code):
            continue
        if not is_generation_supported(code):
            continue
        probe = probe_for_skill(code)
        examples = [
            {
                "id": case.id,
                "age": case.data.age_years,
                "grade": case.data.grade,
                "mode": case.expected_mode.value,
                "why": case.label,
            }
            for case in cases
            if case.expected_skill == code
        ][:4]
        sections.append(
            {
                "skill": code,
                "display_name": item["display_name"],
                "grade_band": f"{item['grade_band_min']}–{item['grade_band_max']}",
                "prerequisites": list(prerequisites_for(code)),
                "measurable_outcome": item.get("measurable_outcome"),
                "probe": probe.get("observable_task"),
                "success_criterion": probe.get("success_criteria"),
                "expected_outcome": probe.get("expected_outcome"),
                "standards": [
                    {
                        "code": ref["standard_code"],
                        "note": ref.get("note", ""),
                    }
                    for ref in SKILL_STANDARD_REFS
                    if ref["skill_code"] == code
                ],
                "planner_examples": examples,
            }
        )
    return sections


def curriculum_review_markdown() -> str:
    lines = [
        "# Daily Win curriculum review",
        "",
        "Educator-facing snapshot of active academic skills. Not learner data.",
        "",
    ]
    for section in curriculum_review_sections():
        lines.extend(
            [
                f"## {section['display_name']}",
                "",
                f"- Skill: `{section['skill']}`",
                f"- Grade band (age years): {section['grade_band']}",
                f"- Prerequisites: {_join_codes(section['prerequisites'])}",
                f"- Measurable outcome: {section['measurable_outcome']}",
                f"- Probe: {section['probe']}",
                f"- Success criterion: {section['success_criterion']}",
                f"- Expected outcome: {section['expected_outcome']}",
            ]
        )
        standards = section["standards"]
        if standards:
            for ref in standards:
                note = f" — {ref['note']}" if ref["note"] else ""
                lines.append(f"- Standard: `{ref['code']}`{note}")
        else:
            lines.append("- Standard: none")
        examples = section["planner_examples"]
        if examples:
            lines.append("- Planner examples:")
            for example in examples:
                lines.append(
                    f"  - {example['id']} (age {example['age']}, grade "
                    f"{example['grade']}, {example['mode']}): {example['why']}"
                )
        else:
            lines.append("- Planner examples: none yet")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _join_codes(codes: list[str]) -> str:
    if not codes:
        return "none"
    return ", ".join(f"`{code}`" for code in codes)
