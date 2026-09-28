"""Challenge calibration from explicit signals. No opaque score."""

from __future__ import annotations

TOO_EASY = "too_easy"
PRODUCTIVE = "productive_challenge"
TOO_HARD = "too_hard"


def classify_challenge(
    *,
    difficulty: str | None,
    academic_result: str | None,
    performance_effort: str | None,
    setback_response: str | None,
    completion: str | None,
) -> str:
    if difficulty == "too_easy":
        return TOO_EASY
    if difficulty == "too_hard":
        return TOO_HARD
    if academic_result == "correct_independently" and performance_effort == "automatic":
        return TOO_EASY
    if setback_response == "stopped_or_avoided" or completion == "stopped_early":
        return TOO_HARD
    if academic_result in {
        "incorrect",
        "correct_after_significant_help",
        "not_attempted",
    }:
        return TOO_HARD
    return PRODUCTIVE


def should_reduce_complexity(
    *,
    academic_result: str | None,
    setback_response: str | None,
    repeated_significant_support: bool,
) -> bool:
    if repeated_significant_support:
        return True
    if academic_result == "correct_after_significant_help":
        return True
    return setback_response in {"needed_significant_help", "stopped_or_avoided"}
