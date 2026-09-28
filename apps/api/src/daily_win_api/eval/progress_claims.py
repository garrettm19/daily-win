"""Parent-facing Progress copy must not overclaim."""

import re

from daily_win_api.domains.daily_wins.insight import parent_insight
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.domains.learning.presentation import (
    EVIDENCE_DISCLAIMER,
    STATE_GUIDE,
    academic_next_copy,
    academic_observation,
    academic_state_label,
    academic_supporting_copy,
    session_evidence_label,
    what_changed_today,
)
from daily_win_api.domains.learning.progress import STILL_LEARNING

_OVERCLAIM = re.compile(
    r"\b(advanced|mastery|mastered|percentile|gifted|below grade|failed|regressed|"
    r"grade level|standardized|learns best|visual learner|learning style)\b",
    re.IGNORECASE,
)

_RECENT_EVIDENCE_COPY = (
    "Completed independently.",
    "Completed with a little help.",
    "Completed with a lot of help.",
    "Didn't get it yet.",
    "Didn't try this part.",
)


def parent_facing_strings() -> tuple[str, ...]:
    values: list[str] = [
        EVIDENCE_DISCLAIMER,
        STILL_LEARNING,
        *_RECENT_EVIDENCE_COPY,
        session_evidence_label(1),
        session_evidence_label(3),
    ]
    values.extend(f"{label}. {explanation}" for label, explanation in STATE_GUIDE)
    for band in AcademicBand:
        values.append(academic_state_label(band))
        values.append(
            academic_supporting_copy(band, session_count=1, needs_remediation=False)
        )
        values.append(
            academic_supporting_copy(band, session_count=3, needs_remediation=False)
        )
        for result in AcademicResult:
            values.append(
                academic_next_copy(result, needs_remediation=False, band=band)
            )
    values.append(academic_state_label(AcademicBand.DEVELOPING, needs_remediation=True))
    values.append(
        academic_supporting_copy(
            AcademicBand.DEVELOPING, session_count=4, needs_remediation=True
        )
    )
    for result in AcademicResult:
        values.append(academic_observation("Hayes", result, first_evidence=True))
        values.append(academic_observation("Hayes", result, first_evidence=False))
    values.append(
        what_changed_today(
            has_prior_wins=True,
            skill_display_name="Add within 10",
            reason_codes=("prerequisite_evidence_missing",),
            instruction_mode="practice",
            scaffold="one_prompt",
            growth_summary=None,
        )
        or ""
    )
    insight = parent_insight("Hayes", "continued_after_prompt")
    values.append(insight["observation"])
    values.append(insight["next_adjustment"])
    return tuple(item for item in values if item)


def overclaim_hits(texts: tuple[str, ...] | None = None) -> tuple[str, ...]:
    found: list[str] = []
    for text in texts or parent_facing_strings():
        match = _OVERCLAIM.search(text)
        if match:
            found.append(f"{match.group(0)} in {text}")
    return tuple(found)
