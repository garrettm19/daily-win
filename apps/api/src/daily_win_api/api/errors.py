from fastapi.responses import JSONResponse

from daily_win_api.ai.error_codes import sanitize_error_code


class SanitizedClientError(Exception):
    """HTTP error with a safe human message and optional sanitized error_code."""

    def __init__(self, status_code: int, detail: str, error_code: str) -> None:
        sanitized = sanitize_error_code(error_code)
        super().__init__(sanitized)
        self.status_code = status_code
        self.detail = detail
        self.error_code = sanitized


def generation_error_payload(
    detail: str, error_code: str, *, include_error_code: bool
) -> dict[str, str]:
    payload = {"detail": detail}
    if include_error_code:
        payload["error_code"] = sanitize_error_code(error_code)
    return payload


def sanitized_error_response(
    *,
    status_code: int,
    detail: str,
    error_code: str,
    include_error_code: bool,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=generation_error_payload(
            detail, error_code, include_error_code=include_error_code
        ),
    )
