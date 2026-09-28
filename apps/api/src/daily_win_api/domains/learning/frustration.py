"""Deterministic frustration responses. Dignity over pressure."""

from __future__ import annotations

MILD_ENGAGED = "mild_frustrated_engaged"
REPEATED_FAILURE = "repeated_failure"
DISENGAGED = "disengaged"


def classify_frustration(
    *,
    notice_chips: tuple[str, ...] = (),
    setback_response: str | None = None,
    completion: str | None = None,
    academic_result: str | None = None,
) -> str | None:
    if (
        setback_response == "stopped_or_avoided"
        or completion == "stopped_early"
        or "lost interest" in notice_chips
    ):
        return DISENGAGED
    if (
        setback_response == "needed_significant_help"
        or academic_result in {"incorrect", "correct_after_significant_help"}
    ):
        return REPEATED_FAILURE
    if "got frustrated" in notice_chips or setback_response == "continued_after_prompt":
        return MILD_ENGAGED
    return None


def frustration_guidance(kind: str) -> tuple[str, ...]:
    if kind == MILD_ENGAGED:
        return (
            "Acknowledge that this one is tricky.",
            "Give them another moment to think.",
            "Ask a strategy question, then continue.",
        )
    if kind == REPEATED_FAILURE:
        return (
            "Give an appropriate scaffold.",
            "Reduce one step if needed. Keep the same skill.",
        )
    return (
        "Shorten or reset the activity.",
        "Preserve dignity. Stopping is not a character failure.",
        "Collect the evidence and let tomorrow's plan adapt.",
    )
