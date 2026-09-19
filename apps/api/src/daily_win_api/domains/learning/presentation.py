"""Parent-facing copy for academic and growth loops. Not learner truth."""

from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    InstructionMode,
    ProbeType,
    ScaffoldLevel,
)
from daily_win_api.domains.learning.taxonomy import (
    is_academic_code,
    is_growth_or_life_code,
)

STATE_GUIDE = (
    ("Emerging", "Starting to show the skill."),
    ("Developing", "Showing the skill, sometimes with support."),
    ("Demonstrated", "Shown independently across multiple activities."),
    ("Retained", "Shown independently again after time has passed."),
)

EVIDENCE_DISCLAIMER = (
    "These are based only on Daily Win activities and your observations."
)

_BAND_LABEL = {
    AcademicBand.NOT_OBSERVED: "Not enough evidence yet",
    AcademicBand.EMERGING: "Emerging",
    AcademicBand.DEVELOPING: "Developing",
    AcademicBand.DEMONSTRATED: "Demonstrated",
    AcademicBand.RETAINED: "Retained",
}

_DOMAIN_LABEL = {
    "MATH": "Math",
    "READING": "Reading",
    "WRITING": "Writing",
    "GROWTH": "Growth",
    "LIFE": "Life skills",
}

_REASON_LABEL = {
    "parent_priority": "Parent priority",
    "insufficient_independent_evidence": "Needs more independent evidence",
    "prerequisite_evidence_missing": "Prerequisite needs more evidence",
    "review_spacing": "Time to revisit",
    "regression_review": "Needs another practice round",
    "age_grade_appropriate": "Age/grade appropriate",
    "progression_next": "Next skill in the sequence",
    "diagnostic_check": "Short independent check",
}

_SCAFFOLD_LABEL = {
    ScaffoldLevel.HIGH: "High",
    ScaffoldLevel.MEDIUM: "Medium",
    ScaffoldLevel.LOW: "Low",
}

_MODE_LABEL = {
    InstructionMode.INTRODUCE: "Introduce",
    InstructionMode.PRACTICE: "Practice",
    InstructionMode.REVIEW: "Review",
    InstructionMode.REMEDIATION: "Practice",
    InstructionMode.DIAGNOSTIC: "Quick check",
}

_RESULT_VERB = {
    AcademicResult.CORRECT_INDEPENDENTLY: "completed the {skill} task independently",
    AcademicResult.CORRECT_AFTER_LIGHT_PROMPT: (
        "completed the {skill} task with a little help"
    ),
    AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP: (
        "completed the {skill} task with a lot of help"
    ),
    AcademicResult.INCORRECT: "didn't get the {skill} task yet",
    AcademicResult.NOT_ATTEMPTED: "didn't try this {skill} part",
}


def academic_observation(
    nickname: str,
    result: AcademicResult,
    *,
    first_evidence: bool,
    skill_display_name: str = "planned",
) -> str:
    skill = _lower_first(skill_display_name) or "planned"
    line = f"{nickname} {_RESULT_VERB[result].format(skill=skill)}."
    if first_evidence:
        return (
            f"{line} Daily Win is still learning how independently "
            f"{nickname} can do this skill."
        )
    return line


def domain_label(domain: str) -> str:
    return _DOMAIN_LABEL.get(domain, domain.title())


def academic_state_label(band: AcademicBand, *, needs_remediation: bool = False) -> str:
    if needs_remediation:
        return "Ready for another practice round"
    return _BAND_LABEL[band]


def academic_supporting_copy(
    band: AcademicBand, *, session_count: int, needs_remediation: bool
) -> str:
    if needs_remediation:
        return "Ready for another practice round"
    if band in {AcademicBand.NOT_OBSERVED, AcademicBand.EMERGING} or session_count < 2:
        return "Daily Win is still gathering evidence."
    if band is AcademicBand.DEVELOPING:
        return "Daily Win is still gathering evidence."
    if band is AcademicBand.DEMONSTRATED:
        return "Shown independently more than once. Not yet after a gap in time."
    return "Shown independently again after time has passed."


def probe_asks_for_counts(probe: dict[str, object] | None) -> bool:
    if not probe:
        return False
    probe_type = str(probe.get("probe_type") or "")
    return probe_type == ProbeType.COUNTED_ITEMS.value or bool(
        probe.get("attempt_structure")
    )


def is_academic_probe(probe: dict[str, object] | None, primary_skill_code: str) -> bool:
    if not is_academic_code(primary_skill_code):
        return False
    if not probe:
        return False
    target = probe.get("target_skill_code")
    return isinstance(target, str) and target == primary_skill_code


def what_to_check(nickname: str, observable_task: str) -> str:
    task = observable_task.strip().rstrip(".")
    if not task:
        return f"Can {nickname} try the planned skill?"
    lowered = task[0].lower() + task[1:] if task[0].isupper() else task
    if task.lower().startswith(("can ", "does ", "did ")):
        return f"{task}?"
    return f"Can {nickname} {lowered}?"


def success_looks_like(expected_outcome: str) -> str:
    text = expected_outcome.strip()
    if text.endswith("."):
        return text
    return f"{text}."


def shortened_task(observable_task: str) -> str:
    task = observable_task.strip().rstrip(".")
    if len(task) <= 72:
        return task
    return task[:69].rstrip() + "…"


def academic_next_copy(
    result: AcademicResult, *, needs_remediation: bool, band: AcademicBand
) -> str:
    if needs_remediation or result in {
        AcademicResult.INCORRECT,
        AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP,
    }:
        return "We'll practice this skill again with more support."
    if result is AcademicResult.CORRECT_AFTER_LIGHT_PROMPT:
        return "We'll practice this skill again with a little less support."
    if result is AcademicResult.CORRECT_INDEPENDENTLY:
        if band is AcademicBand.RETAINED:
            return "We'll keep this skill in rotation so it stays fresh."
        if band is AcademicBand.DEMONSTRATED:
            return "We'll keep practicing until this skill holds over time."
        return "We'll practice this skill again with a little less support."
    return "We'll keep gathering evidence on this skill."


def reason_labels(codes: list[str] | tuple[str, ...]) -> list[str]:
    return [
        _REASON_LABEL.get(code, code.replace("_", " ").capitalize()) for code in codes
    ]


def scaffold_label(raw: str) -> str:
    try:
        return _SCAFFOLD_LABEL[ScaffoldLevel(raw)]
    except ValueError:
        return raw.replace("_", " ").capitalize()


def mode_label(raw: str) -> str:
    try:
        return _MODE_LABEL[InstructionMode(raw)]
    except ValueError:
        return raw.replace("_", " ").capitalize()


def difficulty_debug_label(academic_band: str | None) -> str:
    if not academic_band:
        return "Not enough evidence yet"
    try:
        return _BAND_LABEL[AcademicBand(academic_band)]
    except ValueError:
        return academic_band.replace("_", " ").capitalize()


def what_changed_today(
    *,
    has_prior_wins: bool,
    skill_display_name: str,
    reason_codes: list[str] | tuple[str, ...],
    instruction_mode: str,
    scaffold: str,
    growth_summary: str | None,
) -> str | None:
    if not has_prior_wins:
        return None
    reasons = set(reason_codes)
    skill = _lower_first(skill_display_name) or "this skill"
    if (
        "regression_review" in reasons
        or instruction_mode == InstructionMode.REMEDIATION.value
    ):
        return (
            f"We're revisiting {skill} after the last activity needed more support."
        )
    if "review_spacing" in reasons or instruction_mode == InstructionMode.REVIEW.value:
        return f"We're trying {skill} again after some time has passed."
    if "prerequisite_evidence_missing" in reasons:
        return "We're practicing the building-block skill first."
    if (
        "diagnostic_check" in reasons
        or instruction_mode == InstructionMode.DIAGNOSTIC.value
    ):
        return (
            f"We're doing a short independent check of {skill} "
            "before longer practice."
        )
    if scaffold == ScaffoldLevel.MEDIUM.value:
        return f"We're practicing {skill} again, but with a little less help this time."
    if scaffold == ScaffoldLevel.HIGH.value:
        return f"We're practicing {skill} again with clear support."
    if growth_summary:
        return growth_summary
    return f"We're practicing {skill} again."


def asks_about_setback(growth_target_code: str | None, *, has_plan: bool) -> bool:
    if not has_plan:
        return True
    if growth_target_code is None:
        return False
    return is_growth_or_life_code(growth_target_code)


def session_evidence_label(count: int) -> str:
    if count == 1:
        return "1 session"
    return f"{count} sessions"


def _lower_first(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped[0].lower() + stripped[1:]
