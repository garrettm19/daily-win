SANITIZED_ERROR_CODES = frozenset(
    {
        "invalid_api_key",
        "permission_denied",
        "insufficient_quota",
        "rate_limited",
        "provider_timeout",
        "provider_connection_error",
        "provider_bad_request",
        "provider_server_error",
        "provider_error",
        "unsafe_content",
        "schema_validation_failed",
        "configuration_error",
        "unknown_skill",
        "primary_goal_mismatch",
        "demo_unavailable",
        "feedback_required",
        "already_submitted",
    }
)

_ERROR_CODE_ALIASES = {
    "not_configured": "configuration_error",
    "unsupported_provider": "configuration_error",
    "empty_structured_output": "schema_validation_failed",
}


def sanitize_error_code(code: str | None) -> str:
    """Return an allowlisted machine-readable code. Never pass through raw text."""
    if code in SANITIZED_ERROR_CODES:
        return code
    if code in _ERROR_CODE_ALIASES:
        return _ERROR_CODE_ALIASES[code]
    return "provider_error"
