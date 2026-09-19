import re
from dataclasses import dataclass

from daily_win_api.domains.learning.probes import GENERIC_PROBE_TASK, probe_for_skill
from daily_win_api.domains.learning.taxonomy import (
    SKILL_DEFINITIONS,
    is_academic_code,
    is_generation_supported,
)

_AFFECT = re.compile(
    r"\b(enjoy|fun|like|love|neat|tidy|handwriting|pretty|try hard|tried hard)\b",
    re.IGNORECASE,
)
_TOO_LONG = re.compile(
    r"\b(chapter book|entire chapter|full book|timed fluency passage|"
    r"30 minutes|whole worksheet)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProbeCase:
    id: str
    skill_code: str
    probe: dict[str, object]
    expected_valid: bool
    reason: str


def labelled_probe_cases() -> tuple[ProbeCase, ...]:
    catalog = [
        ProbeCase(
            id=f"catalog_{code}",
            skill_code=code,
            probe=probe_for_skill(code),
            expected_valid=True,
            reason="every active academic skill must have a construct-specific probe",
        )
        for code in (
            str(item["code"])
            for item in SKILL_DEFINITIONS
            if item.get("skill_kind") == "skill"
            and is_academic_code(str(item["code"]))
            and is_generation_supported(str(item["code"]))
        )
    ]
    bad = (
        ProbeCase(
            id="bad_enjoy_story",
            skill_code="reading.comprehension.main_idea",
            probe={
                "target_skill_code": "reading.comprehension.main_idea",
                "observable_task": "Did the child enjoy the story?",
                "expected_outcome": "Child had fun.",
                "success_criteria": "Smiled or said they liked it.",
            },
            expected_valid=False,
            reason="Affect is not comprehension",
        ),
        ProbeCase(
            id="bad_neat_writing",
            skill_code="writing.organization.sequence_events",
            probe={
                "target_skill_code": "writing.organization.sequence_events",
                "observable_task": "Did the child write neatly?",
                "expected_outcome": "Handwriting is tidy.",
                "success_criteria": "Letters sit on the line.",
            },
            expected_valid=False,
            reason="Neatness is not organization",
        ),
        ProbeCase(
            id="bad_wrong_target",
            skill_code="math.addition.within_10",
            probe={
                "target_skill_code": "math.addition.within_20",
                "observable_task": "Solve one addition fact whose sum is 10 or less.",
                "expected_outcome": "Child states the correct sum.",
                "success_criteria": "Correct independently.",
            },
            expected_valid=False,
            reason="Probe targets a different skill",
        ),
        ProbeCase(
            id="bad_effort_only",
            skill_code="math.addition.within_10",
            probe={
                "target_skill_code": "math.addition.within_10",
                "observable_task": "Did the child try hard?",
                "expected_outcome": "Child tried hard.",
                "success_criteria": "Tried hard.",
            },
            expected_valid=False,
            reason="Effort is not the addition construct",
        ),
        ProbeCase(
            id="bad_generic_fallback",
            skill_code="math.addition.within_10",
            probe={
                "target_skill_code": "math.addition.within_10",
                "observable_task": GENERIC_PROBE_TASK,
                "expected_outcome": "The child attempts the planned skill.",
                "success_criteria": "Independent try.",
            },
            expected_valid=False,
            reason="Generic fallback does not measure the construct",
        ),
        ProbeCase(
            id="bad_missing_success",
            skill_code="reading.comprehension.main_idea",
            probe={
                "target_skill_code": "reading.comprehension.main_idea",
                "observable_task": "Ask what the passage was mostly about.",
                "expected_outcome": "Child states the central idea.",
                "success_criteria": "",
            },
            expected_valid=False,
            reason="Success criterion must be explicit",
        ),
        ProbeCase(
            id="good_sequence",
            skill_code="writing.organization.sequence_events",
            probe=probe_for_skill("writing.organization.sequence_events"),
            expected_valid=True,
            reason="Orders events, which is the construct",
        ),
        ProbeCase(
            id="good_main_idea",
            skill_code="reading.comprehension.main_idea",
            probe=probe_for_skill("reading.comprehension.main_idea"),
            expected_valid=True,
            reason="Asks what the passage was mostly about",
        ),
    )
    return tuple(catalog) + bad


def probe_is_valid(skill_code: str, probe: dict[str, object]) -> bool:
    target = probe.get("target_skill_code")
    if target != skill_code:
        return False
    task = str(probe.get("observable_task") or "")
    outcome = str(probe.get("expected_outcome") or "")
    success = str(probe.get("success_criteria") or "")
    blob = f"{task} {outcome} {success}"
    if _AFFECT.search(blob):
        return False
    if _TOO_LONG.search(blob):
        return False
    if task.strip() == GENERIC_PROBE_TASK:
        return False
    return bool(task.strip() and outcome.strip() and success.strip())


def evaluate_probe_case(case: ProbeCase) -> list[str]:
    valid = probe_is_valid(case.skill_code, case.probe)
    if valid is case.expected_valid:
        return []
    return [
        f"{case.id}: valid={valid} expected={case.expected_valid} ({case.reason})"
    ]
