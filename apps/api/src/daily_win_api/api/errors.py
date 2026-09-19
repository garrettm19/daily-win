from fastapi.responses import JSONResponse

from daily_win_api.ai.error_codes import sanitize_error_code
from daily_win_api.domains.daily_wins.renderer_contract import HARD_RULE_CODES
from daily_win_api.domains.daily_wins.safety import SAFETY_RULE_CODES


class SanitizedClientError(Exception):
    """HTTP error with a safe human message and optional sanitized error_code."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        *,
        dev_reason: str | None = None,
    ) -> None:
        sanitized = sanitize_error_code(error_code)
        super().__init__(sanitized)
        self.status_code = status_code
        self.detail = detail
        self.error_code = sanitized
        self.dev_reason = sanitize_dev_reason(dev_reason)


def sanitize_dev_reason(reason: str | None) -> str | None:
    """Allowlisted safety or renderer-contract rule only. Never generated text."""
    if reason in SAFETY_RULE_CODES or reason in HARD_RULE_CODES:
        return reason
    return None


def generation_error_payload(
    detail: str,
    error_code: str,
    *,
    include_error_code: bool,
    dev_reason: str | None = None,
) -> dict[str, str]:
    payload = {"detail": detail}
    if include_error_code:
        payload["error_code"] = sanitize_error_code(error_code)
        sanitized_reason = sanitize_dev_reason(dev_reason)
        if sanitized_reason is not None:
            payload["dev_reason"] = sanitized_reason
    return payload


def sanitized_error_response(
    *,
    status_code: int,
    detail: str,
    error_code: str,
    include_error_code: bool,
    dev_reason: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=generation_error_payload(
            detail,
            error_code,
            include_error_code=include_error_code,
            dev_reason=dev_reason,
        ),
    )
