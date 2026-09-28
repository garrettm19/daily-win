"""placement_policy_v1 — age/grade starting prior. Evidence determines level."""

from __future__ import annotations

from dataclasses import dataclass

from daily_win_api.domains.learning.academic import AcademicStateSnapshot
from daily_win_api.domains.learning.enums import AcademicBand
from daily_win_api.domains.learning.prerequisites import prerequisites_for
from daily_win_api.domains.learning.probes import probe_for_skill
from daily_win_api.domains.learning.taxonomy import (
    child_skills_for_parent,
    definition_by_code,
    is_academic_code,
    is_generation_supported,
)

PLACEMENT_POLICY_V1 = "placement_policy_v1"
PLACEMENT_POLICY_CURRENT = PLACEMENT_POLICY_V1


@dataclass(frozen=True)
class PlacementSkillMeta:
    code: str
    entry_age_min: int
    entry_age_max: int
    entry_label: str
    initial_diagnostic_target: bool
    foundation_for_older: bool


@dataclass(frozen=True)
class PlacementDecision:
    skill_code: str
    sparse_evidence: bool
    reason_codes: tuple[str, ...]
    entry_label: str
    why: str
    presentation_constraint: str | None
    policy_version: str = PLACEMENT_POLICY_CURRENT


def _meta(
    code: str,
    *,
    age_min: int,
    age_max: int,
    label: str,
    diagnostic: bool = True,
    foundation: bool = False,
) -> PlacementSkillMeta:
    return PlacementSkillMeta(
        code=code,
        entry_age_min=age_min,
        entry_age_max=age_max,
        entry_label=label,
        initial_diagnostic_target=diagnostic,
        foundation_for_older=foundation,
    )


PLACEMENT_SKILLS: dict[str, PlacementSkillMeta] = {
    "math.number_sense.counting": _meta(
        "math.number_sense.counting",
        age_min=5,
        age_max=6,
        label="Kindergarten counting",
        foundation=True,
    ),
    "math.number_sense.compare": _meta(
        "math.number_sense.compare",
        age_min=6,
        age_max=7,
        label="Early quantity comparison",
    ),
    "math.addition.within_10": _meta(
        "math.addition.within_10",
        age_min=5,
        age_max=7,
        label="Grade K–1 addition within 10",
    ),
    "math.addition.within_20": _meta(
        "math.addition.within_20",
        age_min=7,
        age_max=8,
        label="Grade 2 addition within 20",
    ),
    "math.addition.word_problems": _meta(
        "math.addition.word_problems",
        age_min=8,
        age_max=9,
        label="Grade 3 addition stories",
    ),
    "math.subtraction.within_10": _meta(
        "math.subtraction.within_10",
        age_min=5,
        age_max=7,
        label="Grade K–1 subtraction within 10",
    ),
    "math.subtraction.within_20": _meta(
        "math.subtraction.within_20",
        age_min=7,
        age_max=8,
        label="Grade 2 subtraction within 20",
    ),
    "math.multiplication.equal_groups": _meta(
        "math.multiplication.equal_groups",
        age_min=8,
        age_max=9,
        label="Grade 3 equal groups",
    ),
    "math.fractions.halves_fourths": _meta(
        "math.fractions.halves_fourths",
        age_min=6,
        age_max=9,
        label="Grade 1–2 halves and fourths",
    ),
    "reading.phonics.letter_sounds": _meta(
        "reading.phonics.letter_sounds",
        age_min=5,
        age_max=6,
        label="Kindergarten letter sounds",
        foundation=True,
    ),
    "reading.phonics.blend_cvc": _meta(
        "reading.phonics.blend_cvc",
        age_min=6,
        age_max=7,
        label="Grade 1 CVC blending",
        foundation=True,
    ),
    "reading.fluency.smooth_oral": _meta(
        "reading.fluency.smooth_oral",
        age_min=6,
        age_max=8,
        label="Grade 1–2 oral reading",
    ),
    "reading.vocabulary.context_clues": _meta(
        "reading.vocabulary.context_clues",
        age_min=7,
        age_max=9,
        label="Grade 2–3 context clues",
    ),
    "reading.comprehension.recall_details": _meta(
        "reading.comprehension.recall_details",
        age_min=6,
        age_max=8,
        label="Grade 1–2 recall",
    ),
    "reading.comprehension.main_idea": _meta(
        "reading.comprehension.main_idea",
        age_min=7,
        age_max=9,
        label="Grade 2–3 main idea",
    ),
    "reading.comprehension.simple_inference": _meta(
        "reading.comprehension.simple_inference",
        age_min=8,
        age_max=9,
        label="Grade 3–4 simple inference",
    ),
    "writing.spelling.cvc": _meta(
        "writing.spelling.cvc",
        age_min=5,
        age_max=6,
        label="Kindergarten–1 CVC spelling",
        foundation=True,
    ),
    "writing.spelling.patterns": _meta(
        "writing.spelling.patterns",
        age_min=6,
        age_max=8,
        label="Grade 1–2 spelling patterns",
    ),
    "writing.spelling.endings_suffixes": _meta(
        "writing.spelling.endings_suffixes",
        age_min=8,
        age_max=9,
        label="Grade 3 endings and suffixes",
    ),
    "writing.spelling.multisyllabic_irregular": _meta(
        "writing.spelling.multisyllabic_irregular",
        age_min=9,
        age_max=9,
        label="Grade 3–4 longer and irregular words",
    ),
    "writing.sentences.complete_sentence": _meta(
        "writing.sentences.complete_sentence",
        age_min=5,
        age_max=8,
        label="Grade K–2 complete sentences",
    ),
    "writing.organization.sequence_events": _meta(
        "writing.organization.sequence_events",
        age_min=6,
        age_max=8,
        label="Grade 1–2 event sequence",
    ),
    "writing.organization.topic_details": _meta(
        "writing.organization.topic_details",
        age_min=8,
        age_max=9,
        label="Grade 3 topic details",
    ),
}


def placement_pool(goal_code: str) -> list[str]:
    catalog = definition_by_code()
    if goal_code not in catalog:
        return []
    item = catalog[goal_code]
    if item.get("skill_kind") == "strand":
        return [
            str(child["code"])
            for child in child_skills_for_parent(goal_code)
            if is_generation_supported(str(child["code"]))
        ]
    parent = str(item.get("parent_code") or "")
    if not parent:
        return [goal_code] if is_generation_supported(goal_code) else []
    ceiling = int(item["progression_position"])
    return [
        str(child["code"])
        for child in child_skills_for_parent(parent)
        if is_generation_supported(str(child["code"]))
        and int(child["progression_position"]) <= ceiling
    ]


def strand_is_sparse(pool: list[str], states: dict) -> bool:
    for code in pool:
        snap = _snapshot(code, states)
        if snap is None:
            continue
        if snap.needs_remediation:
            return False
        if snap.band is not AcademicBand.NOT_OBSERVED:
            return False
    return True


def observed_weak(snapshot: AcademicStateSnapshot | None) -> bool:
    if snapshot is None:
        return False
    if snapshot.needs_remediation:
        return True
    if snapshot.band in {AcademicBand.EMERGING, AcademicBand.DEVELOPING}:
        return True
    return False


def is_unknown(snapshot: AcademicStateSnapshot | None) -> bool:
    return snapshot is None or snapshot.band is AcademicBand.NOT_OBSERVED


def should_step_down(
    code: str, snapshot: AcademicStateSnapshot | None, states: dict
) -> bool:
    if snapshot is None:
        return False
    if snapshot.last_independent_success_at is not None:
        return False
    if snapshot.band is not AcademicBand.EMERGING:
        return False
    if snapshot.distinct_session_count < 1:
        return False
    if _meta_for(code).foundation_for_older:
        return False
    down = direct_step_down(code)
    if down is None:
        return False
    return is_unknown(_snapshot(down, states)) or observed_weak(_snapshot(down, states))


def direct_step_down(code: str) -> str | None:
    for prereq in reversed(prerequisites_for(code)):
        if is_generation_supported(prereq) and is_academic_code(prereq):
            return prereq
    return None


def select_entry_skill(pool: list[str], age_years: int) -> str | None:
    if not pool:
        return None
    catalog = definition_by_code()
    fitting = [
        code
        for code in pool
        if _meta_for(code).entry_age_min <= age_years
        and _meta_for(code).initial_diagnostic_target
    ]
    if not fitting:
        return pool[0]
    return max(
        fitting,
        key=lambda code: int(catalog[code]["progression_position"]),
    )


def remap_generation_goal(goal_code: str) -> str:
    if is_generation_supported(goal_code):
        return goal_code
    catalog = definition_by_code()
    parent = str(catalog.get(goal_code, {}).get("parent_code") or "")
    return parent or goal_code


def presentation_constraint_for(code: str, age_years: int) -> str | None:
    if age_years >= 8 and _meta_for(code).foundation_for_older:
        return "age_respectful_foundation"
    return None


def decide_placement(goal_code: str, age_years: int, states: dict) -> PlacementDecision:
    goal_code = remap_generation_goal(goal_code)
    pool = placement_pool(goal_code)
    sparse = strand_is_sparse(pool, states)
    entry = select_entry_skill(pool, age_years) or (pool[-1] if pool else goal_code)
    meta = _meta_for(entry)
    constraint = presentation_constraint_for(entry, age_years)
    if sparse:
        why = (
            "New learner; starting near reported grade level. "
            "Age/grade is a starting prior, not mastery."
        )
        return PlacementDecision(
            skill_code=entry,
            sparse_evidence=True,
            reason_codes=("grade_band_prior", "placement_diagnostic"),
            entry_label=meta.entry_label,
            why=why,
            presentation_constraint=constraint,
        )
    return PlacementDecision(
        skill_code=entry,
        sparse_evidence=False,
        reason_codes=("grade_band_prior",),
        entry_label=meta.entry_label,
        why="Enough Daily Win evidence exists to place from learner state.",
        presentation_constraint=constraint,
    )


def placement_probe(
    skill_code: str, *, sparse_diagnostic: bool, age_years: int
) -> dict:
    base = dict(probe_for_skill(skill_code))
    if not sparse_diagnostic:
        return base
    overlay = _DIAGNOSTIC_OVERLAYS.get(skill_code)
    if overlay is None or age_years < 7:
        return base
    merged = {**base, **overlay}
    merged["target_skill_code"] = skill_code
    return merged


def _meta_for(code: str) -> PlacementSkillMeta:
    found = PLACEMENT_SKILLS.get(code)
    if found is not None:
        return found
    catalog = definition_by_code()
    item = catalog.get(code, {})
    return _meta(
        code,
        age_min=int(item.get("grade_band_min") or 5),
        age_max=int(item.get("grade_band_max") or 9),
        label=str(item.get("display_name") or code),
    )


def _snapshot(code: str, states: dict) -> AcademicStateSnapshot | None:
    state = states.get(code)
    if state is None:
        return None
    return getattr(state, "academic", None)


_DIAGNOSTIC_OVERLAYS: dict[str, dict[str, object]] = {
    "writing.spelling.endings_suffixes": {
        "observable_task": (
            "Say four words for the child to spell (no copying): one pattern "
            "word (rain), one suffix word (jumped), one irregular word "
            "(said), and one slightly easier anchor (shop). Record how many "
            "were independent."
        ),
        "attempt_structure": "2-4 words",
        "expected_outcome": (
            "Child independently spells most of the grade-level items; "
            "the easier anchor is a check, not the whole result."
        ),
    },
    "writing.spelling.multisyllabic_irregular": {
        "observable_task": (
            "Say four words for the child to spell (no copying): a pattern "
            "(boat), a suffix (playing), an irregular or longer word "
            "(because), and one easier anchor (rain). Record independent "
            "spellings. Do not turn this into a test packet."
        ),
        "attempt_structure": "2-4 words",
        "expected_outcome": (
            "Child independently spells the grade-appropriate items; "
            "the easier word is only an anchor."
        ),
    },
    "writing.spelling.patterns": {
        "observable_task": (
            "Say three pattern words (rain, boat, shop) and ask the child "
            "to write them. One may be an easier CVC anchor."
        ),
        "attempt_structure": "2-4 words",
    },
    "math.addition.word_problems": {
        "observable_task": (
            "Tell two short oral 'how many in all' stories with totals "
            "of 10 or less, then one slightly easier within-10 fact. "
            "Do not say 'add'. Record independent answers."
        ),
        "attempt_structure": "2-3 items",
    },
    "math.addition.within_20": {
        "observable_task": (
            "Ask two addition facts with sums 11–20 and one within-10 "
            "anchor. Objects or fingers allowed."
        ),
        "attempt_structure": "2-3 facts",
    },
    "reading.comprehension.simple_inference": {
        "observable_task": (
            "Read two short 1–2 sentence items that imply something "
            "unstated. Ask one 'how do you know' question per item."
        ),
        "attempt_structure": "2 items",
    },
    "reading.comprehension.main_idea": {
        "observable_task": (
            "Read two very short texts. Ask what each is mostly about."
        ),
        "attempt_structure": "2 items",
    },
    "math.multiplication.equal_groups": {
        "observable_task": (
            "Show two quick equal-group pictures (2–3 groups of ≤5) and "
            "ask for the totals."
        ),
        "attempt_structure": "2 items",
    },
}
