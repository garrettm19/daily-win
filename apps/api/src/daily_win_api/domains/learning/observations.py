"""Typed parent observations. Never silently become academic mastery."""

from __future__ import annotations

ALLOWED_SELF_CORRECTION = frozenset(
    {
        "self_corrected",
        "corrected_after_prompt",
        "did_not_correct",
        "not_observed",
    }
)
ALLOWED_EFFORT = frozenset(
    {
        "automatic",
        "effortful_but_independent",
        "effortful_with_support",
        "not_observed",
    }
)
ALLOWED_BONUS_ENGAGEMENT = frozenset(
    {
        "loved_it",
        "liked_it",
        "neutral",
        "not_into_it",
        "skipped",
    }
)
ALLOWED_NOTICE_CHIPS = frozenset(
    {
        "self-corrected",
        "explained reasoning",
        "taught the coach",
        "worked automatically",
        "used a strategy",
        "asked for help",
        "got frustrated",
        "kept trying",
        "lost interest",
        "non-target error noticed",
    }
)
ALLOWED_STRATEGY = frozenset(
    {
        "mental_automatic",
        "counted",
        "drew_modelled",
        "decomposed_numbers",
        "needed_help",
        "guessed_unclear",
        "sounded_out",
        "reread",
        "used_context",
        "recalled_directly",
        "needed_prompt",
        "used_known_pattern",
        "reread_own_work",
        "self_corrected",
        "needed_a_model",
        "not_observed",
    }
)

OBSERVATION_SELF_CORRECTION = "self_correction"
OBSERVATION_STRATEGY = "strategy"
OBSERVATION_EFFORT = "performance_effort"
OBSERVATION_NOTICE = "parent_notice"
OBSERVATION_BONUS_ENGAGEMENT = "bonus_engagement"
OBSERVATION_NON_TARGET = "non_target_error"
OBSERVATION_WIN_OF_WEEK = "win_of_the_week"

SELF_CORRECTION_IS_NOT_FIRST_ATTEMPT = (
    "Self-correction is monitoring evidence. "
    "It does not rewrite a first-attempt result."
)


def observation_payload(
    observation_type: str,
    value: str,
    *,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "observation_type": observation_type,
        "signal": value,
        "reporting_kind": "parent_reported",
        "epistemic_kind": "OBSERVATION",
    }
    if extra:
        payload.update(extra)
    return payload
