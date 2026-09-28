"""Deterministic curriculum audit. Does not expand the taxonomy."""

from dataclasses import dataclass

from daily_win_api.domains.learning.prerequisites import (
    dependents_for,
    prerequisites_for,
)
from daily_win_api.domains.learning.probes import GENERIC_PROBE_TASK, probe_for_skill
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import (
    SKILL_DEFINITIONS,
    definition_by_code,
    is_academic_code,
)

# Remaining reviewed-and-rejected edges. Do not add these.
REJECTED_PREREQUISITE_EDGES: tuple[tuple[str, str], ...] = (
    ("math.number_sense.compare", "math.fractions.halves_fourths"),
)

# No accepted educational gaps remain as "should add" after V0.3.3.
ACTUALLY_MISSING_EDGES: tuple[tuple[str, str], ...] = ()

BROAD_SKILLS: frozenset[str] = frozenset()
HARD_TO_OBSERVE: frozenset[str] = frozenset()
QUESTIONABLE_GRADE_BANDS: frozenset[str] = frozenset()

REMAINING_UNCERTAINTY = (
    "Oral fluency is one 6–8 word familiar sentence, not a passage WCPM score.",
    "Simple inference uses 1–2 sentences; it is not multi-paragraph reasoning.",
    "Equal groups is 2–3 groups of ≤5 objects, not times-table fluency.",
    "Halves/fourths identifies already-split shares; not independent partitioning.",
    "Context clues is one spoken sentence, not dictionary or paragraph clues.",
    "High-frequency spelling is a legacy leaf; new plans use the four-level "
    "spelling progression (CVC → patterns → endings → longer/irregular).",
    "Word problems are oral 'how many in all' stories with totals of 10 or less.",
    "Age/grade is a starting prior for placement diagnostics, not mastery. "
    "Unknown prerequisites are not treated as weakness.",
)


@dataclass(frozen=True)
class SkillAudit:
    code: str
    display_name: str
    measurable_outcome: str | None
    grade_band: tuple[int, int]
    prerequisites: tuple[str, ...]
    next_skills: tuple[str, ...]
    standards: tuple[str, ...]
    evidence_counts: str
    evidence_does_not_count: str
    has_specific_probe: bool
    issues: tuple[str, ...]


@dataclass(frozen=True)
class CurriculumAudit:
    version: str
    skills: tuple[SkillAudit, ...]
    missing_prerequisite_edges: tuple[tuple[str, str], ...]
    overly_broad: tuple[str, ...]
    duplicates: tuple[str, ...]
    hard_to_observe: tuple[str, ...]
    questionable_grade_bands: tuple[str, ...]
    skills_without_specific_probe: tuple[str, ...]
    missing_standard_refs: tuple[str, ...]
    rejected_prerequisite_edges: tuple[tuple[str, str], ...]
    remaining_uncertainty: tuple[str, ...]


def audit_curriculum() -> CurriculumAudit:
    catalog = definition_by_code()
    mapped = {item["skill_code"] for item in SKILL_STANDARD_REFS}
    skills: list[SkillAudit] = []
    missing_probes: list[str] = []
    missing_standards: list[str] = []
    for item in SKILL_DEFINITIONS:
        code = str(item["code"])
        if item.get("skill_kind") != "skill" or not is_academic_code(code):
            continue
        probe = probe_for_skill(code)
        specific = probe.get("observable_task") != GENERIC_PROBE_TASK
        if not specific:
            missing_probes.append(code)
        if code not in mapped:
            missing_standards.append(code)
        issues = _issues_for(code, item, specific, code in mapped)
        skills.append(
            SkillAudit(
                code=code,
                display_name=str(item["display_name"]),
                measurable_outcome=(
                    str(item["measurable_outcome"])
                    if item.get("measurable_outcome")
                    else None
                ),
                grade_band=(
                    int(item["grade_band_min"]),
                    int(item["grade_band_max"]),
                ),
                prerequisites=prerequisites_for(code),
                next_skills=dependents_for(code),
                standards=tuple(
                    ref["standard_code"]
                    for ref in SKILL_STANDARD_REFS
                    if ref["skill_code"] == code
                ),
                evidence_counts=_evidence_counts(code, catalog),
                evidence_does_not_count=_evidence_does_not_count(code),
                has_specific_probe=specific,
                issues=issues,
            )
        )
    return CurriculumAudit(
        version=str(next(iter(catalog.values()))["taxonomy_version"]),
        skills=tuple(skills),
        missing_prerequisite_edges=ACTUALLY_MISSING_EDGES,
        overly_broad=tuple(sorted(BROAD_SKILLS)),
        duplicates=_duplicate_findings(),
        hard_to_observe=tuple(sorted(HARD_TO_OBSERVE)),
        questionable_grade_bands=tuple(sorted(QUESTIONABLE_GRADE_BANDS)),
        skills_without_specific_probe=tuple(missing_probes),
        missing_standard_refs=tuple(missing_standards),
        rejected_prerequisite_edges=REJECTED_PREREQUISITE_EDGES,
        remaining_uncertainty=REMAINING_UNCERTAINTY,
    )


def _issues_for(
    code: str, item: dict[str, object], specific_probe: bool, has_standard: bool
) -> tuple[str, ...]:
    found: list[str] = []
    if code in BROAD_SKILLS:
        found.append("overly_broad")
    if code in HARD_TO_OBSERVE:
        found.append("hard_to_observe_in_short_activity")
    if code in QUESTIONABLE_GRADE_BANDS:
        found.append("questionable_grade_band")
    if not specific_probe:
        found.append("generic_fallback_probe")
    if not has_standard:
        found.append("missing_standard_ref")
    if int(item["grade_band_min"]) < 5 or int(item["grade_band_max"]) > 9:
        found.append("grade_band_outside_product_ages")
    return tuple(found)


def _evidence_counts(code: str, catalog: dict[str, dict[str, object]]) -> str:
    name = str(catalog[code]["display_name"]).lower()
    return (
        f"A parent-reported academic_result on a V4 Daily Win whose "
        f"AssessmentProbe target is {code}. The observable outcome for "
        f"'{name}' was attempted in that session."
    )


def _evidence_does_not_count(code: str) -> str:
    del code
    return (
        "Enjoyment, neatness, effort, time spent, parent guesses about school "
        "level, free-text notes, growth/persistence observations, or a result "
        "from a Daily Win that had no academic probe."
    )


def _duplicate_findings() -> tuple[str, ...]:
    return (
        "1.OA.C.6 legitimately spans addition within 10, addition within 20, "
        "subtraction within 10, and subtraction within 20. Related skills, "
        "not duplicate Daily Win identities.",
    )
