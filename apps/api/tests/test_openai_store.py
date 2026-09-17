from types import SimpleNamespace

import pytest
from openai import RateLimitError

from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.ai.providers.openai import OpenAIModelGateway, map_openai_exception
from daily_win_api.ai.schemas import DailyWinModelContext, ParentReportedBaselineContext


def test_openai_provider_requests_set_store_false() -> None:
    recorder = _RecordingClient()
    gateway = OpenAIModelGateway(
        api_key="test-not-a-real-key",
        model="gpt-5.6-terra",
        client=recorder,
    )

    result = gateway.generate_daily_win(_synthetic_context())

    assert recorder.kwargs is not None
    assert recorder.kwargs["store"] is False
    assert "previous_response_id" not in recorder.kwargs
    assert result.provider == "openai"
    assert result.model == "gpt-5.6-terra"


def test_openai_quota_error_maps_to_insufficient_quota_without_raw_text() -> None:
    raw = (
        "You exceeded your current quota, please check your plan and billing "
        "details at https://platform.openai.com."
    )
    exc = RateLimitError.__new__(RateLimitError)
    Exception.__init__(exc, raw)
    exc.code = "insufficient_quota"
    exc.type = "insufficient_quota"
    exc.body = {
        "message": raw,
        "code": "insufficient_quota",
        "type": "insufficient_quota",
    }

    mapped = map_openai_exception(exc)

    assert mapped.code == "insufficient_quota"
    assert raw not in str(mapped)
    assert "platform.openai.com" not in str(mapped)
    assert "exceeded your current quota" not in str(mapped)


def test_openai_gateway_maps_provider_exceptions() -> None:
    raw = "You exceeded your current quota, please check your plan"
    exc = RateLimitError.__new__(RateLimitError)
    Exception.__init__(exc, raw)
    exc.code = "insufficient_quota"
    exc.type = "insufficient_quota"
    exc.body = {"message": raw, "code": "insufficient_quota"}
    gateway = OpenAIModelGateway(
        api_key="test-not-a-real-key",
        model="gpt-5.6-terra",
        client=_RaisingClient(exc),
    )

    with pytest.raises(ModelGatewayError) as raised:
        gateway.generate_daily_win(_synthetic_context())

    assert raised.value.code == "insufficient_quota"
    assert raw not in str(raised.value)


def _synthetic_context() -> DailyWinModelContext:
    return DailyWinModelContext(
        nickname="Synthetic",
        parent_reported_baseline=ParentReportedBaselineContext(
            age_years=7,
            grade="1",
            interests=[],
            strengths=[],
            current_difficulties=[],
            motivators=[],
            response_to_difficulty=None,
            preferred_activity_minutes=20,
        ),
        active_goals=[],
        primary_goal_skill_code="growth.persistence",
        learner_skill_states=[],
        recent_learning_events=[],
        recent_daily_wins=[],
        allowed_skill_codes=["growth.persistence"],
        allowed_materials=["PAPER"],
    )


class _RecordingClient:
    def __init__(self) -> None:
        self.kwargs: dict | None = None
        self.responses = self

    def parse(self, **kwargs):
        self.kwargs = kwargs
        draft = valid_daily_win_draft()
        return SimpleNamespace(
            output_parsed=draft,
            id="resp_test",
            usage=SimpleNamespace(
                input_tokens=4,
                output_tokens=6,
                total_tokens=10,
            ),
        )


class _RaisingClient:
    def __init__(self, error: Exception) -> None:
        self.responses = self
        self._error = error

    def parse(self, **kwargs):
        raise self._error

