from daily_win_api.ai.error_codes import sanitize_error_code
from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.api.errors import generation_error_payload
from daily_win_api.domains.daily_wins.schemas import CLIENT_GENERATION_FAILED


def test_sanitize_error_code_allowlist_and_aliases() -> None:
    assert sanitize_error_code("insufficient_quota") == "insufficient_quota"
    assert sanitize_error_code("not_configured") == "configuration_error"
    assert sanitize_error_code("empty_structured_output") == (
        "schema_validation_failed"
    )


def test_sanitize_error_code_rejects_raw_provider_text() -> None:
    raw = "You exceeded your current quota, please check your plan"
    assert sanitize_error_code(raw) == "provider_error"
    assert ModelGatewayError(raw).code == "provider_error"
    assert raw not in str(ModelGatewayError(raw))


def test_development_payload_includes_error_code() -> None:
    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "insufficient_quota",
        include_error_code=True,
    )
    assert payload == {
        "detail": CLIENT_GENERATION_FAILED,
        "error_code": "insufficient_quota",
    }


def test_development_payload_includes_allowlisted_dev_reason() -> None:
    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "unsafe_content",
        include_error_code=True,
        dev_reason="sharp_object",
    )
    assert payload["dev_reason"] == "sharp_object"


def test_development_payload_drops_unknown_dev_reason() -> None:
    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "unsafe_content",
        include_error_code=True,
        dev_reason="Use scissors to cut cardboard",
    )
    assert "dev_reason" not in payload


def test_production_payload_omits_error_code() -> None:
    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "insufficient_quota",
        include_error_code=False,
        dev_reason="sharp_object",
    )
    assert payload == {"detail": CLIENT_GENERATION_FAILED}
    assert "error_code" not in payload
    assert "dev_reason" not in payload
