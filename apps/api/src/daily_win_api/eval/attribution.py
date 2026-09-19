"""Eval-only failure ownership. Production still uses the current validator."""

from enum import StrEnum

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.daily_wins.safety import validate_daily_win_safety
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError


class FailureOwner(StrEnum):
    MODEL_OUTPUT_FAILURE = "MODEL_OUTPUT_FAILURE"
    APPLICATION_VALIDATOR_FALSE_POSITIVE = "APPLICATION_VALIDATOR_FALSE_POSITIVE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    SCHEMA_FAILURE = "SCHEMA_FAILURE"
    EVAL_INFRA_FAILURE = "EVAL_INFRA_FAILURE"


def production_safety_status(draft: DailyWinDraft) -> tuple[bool, str | None]:
    """Current application validator. A reject still blocks production."""
    try:
        validate_daily_win_safety(draft)
    except SafetyRejectedError as exc:
        return False, exc.rule
    return True, None


def owner_for_error(error: str | None) -> FailureOwner | None:
    if error is None:
        return None
    if error == "schema_validation_failed":
        return FailureOwner.SCHEMA_FAILURE
    if error in {
        "provider_timeout",
        "provider_connection_error",
        "provider_server_error",
        "provider_bad_request",
        "provider_error",
        "rate_limited",
        "invalid_api_key",
        "insufficient_quota",
        "permission_denied",
        "configuration_error",
    }:
        return FailureOwner.PROVIDER_FAILURE
    return FailureOwner.EVAL_INFRA_FAILURE


def original_safety_was_false_positive(
    *,
    original_hard_failures: list[str],
    current_safety_ok: bool,
) -> bool:
    return (
        "unsafe_content" in original_hard_failures
        and current_safety_ok
    )
