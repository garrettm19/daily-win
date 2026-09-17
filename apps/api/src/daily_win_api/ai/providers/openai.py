import time
from typing import Any

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from daily_win_api.ai.exceptions import ModelGatewayError, ModelGatewaySchemaError
from daily_win_api.ai.prompts.current import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from daily_win_api.ai.schemas import (
    DailyWinDraft,
    DailyWinGenerationResult,
    DailyWinModelContext,
)

PROVIDER_NAME = "openai"


class OpenAIModelGateway:
    """OpenAI Responses API implementation. Domain code must not import this."""

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        self._client = client or OpenAI(api_key=api_key)

    def generate_daily_win(
        self, context: DailyWinModelContext
    ) -> DailyWinGenerationResult:
        started = time.perf_counter()
        try:
            response = self._client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            context.model_dump_json(exclude_none=False)
                        ),
                    },
                ],
                text_format=DailyWinDraft,
                store=False,
            )
        except ModelGatewayError:
            raise
        except Exception as exc:
            raise map_openai_exception(exc) from None
        latency_ms = int((time.perf_counter() - started) * 1000)
        draft = response.output_parsed
        if draft is None:
            raise ModelGatewaySchemaError("schema_validation_failed")

        usage = getattr(response, "usage", None)
        return DailyWinGenerationResult(
            draft=draft,
            provider=PROVIDER_NAME,
            model=self._model,
            prompt_version=PROMPT_VERSION,
            provider_request_id=getattr(response, "id", None),
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
            total_tokens=_usage_value(usage, "total_tokens"),
            latency_ms=latency_ms,
        )


def map_openai_exception(exc: BaseException) -> ModelGatewayError:
    """Map provider exceptions to sanitized codes. Never copy provider text."""
    provider_code = _openai_body_code(exc)
    if isinstance(exc, AuthenticationError):
        return ModelGatewayError("invalid_api_key")
    if isinstance(exc, PermissionDeniedError):
        return ModelGatewayError("permission_denied")
    if isinstance(exc, RateLimitError):
        if provider_code == "insufficient_quota":
            return ModelGatewayError("insufficient_quota")
        return ModelGatewayError("rate_limited")
    if isinstance(exc, APITimeoutError):
        return ModelGatewayError("provider_timeout")
    if isinstance(exc, APIConnectionError):
        return ModelGatewayError("provider_connection_error")
    if isinstance(exc, BadRequestError):
        return ModelGatewayError("provider_bad_request")
    if isinstance(exc, InternalServerError):
        return ModelGatewayError("provider_server_error")
    if isinstance(exc, APIResponseValidationError):
        return ModelGatewaySchemaError("schema_validation_failed")
    if isinstance(exc, APIStatusError):
        status = int(getattr(exc, "status_code", 0) or 0)
        if status == 401:
            return ModelGatewayError("invalid_api_key")
        if status == 403:
            return ModelGatewayError("permission_denied")
        if status == 429:
            if provider_code == "insufficient_quota":
                return ModelGatewayError("insufficient_quota")
            return ModelGatewayError("rate_limited")
        if status >= 500:
            return ModelGatewayError("provider_server_error")
        if status in {400, 422}:
            return ModelGatewayError("provider_bad_request")
    return ModelGatewayError("provider_error")


def _openai_body_code(exc: BaseException) -> str | None:
    for attr in ("code", "type"):
        value = getattr(exc, attr, None)
        if isinstance(value, str) and value:
            return value
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        nested = body.get("error")
        candidate = nested if isinstance(nested, dict) else body
        for key in ("code", "type"):
            value = candidate.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _usage_value(usage: Any, field: str) -> int | None:
    if usage is None:
        return None
    value = getattr(usage, field, None)
    return int(value) if value is not None else None
