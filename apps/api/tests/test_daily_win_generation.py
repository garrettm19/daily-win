from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from daily_win_api.ai.exceptions import (
    ModelGatewayConfigurationError,
    ModelGatewayError,
)
from daily_win_api.ai.providers.fake import FakeModelGateway, valid_daily_win_draft
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.db.session import get_db
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.schemas import (
    AI_RUN_STATUS_REJECTED,
    AI_RUN_STATUS_SUCCEEDED,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.main import create_app


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _route_paths(application) -> set[str]:
    return set(application.openapi().get("paths", {}))


def _ids(session, model) -> set:
    return set(session.scalars(select(model.id)).all())


def _new_row(session, model, before_ids):
    created = _ids(session, model) - before_ids
    assert len(created) == 1
    return session.get(model, created.pop())


def test_valid_fake_daily_win_is_persisted(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway()
    result = generate_demo_daily_win(demo_db, gateway)

    assert result.content.primary_skill_code == "growth.persistence"
    assert result.has_feedback is False
    assert result.content.adaptation_summary is None
    assert len(_ids(demo_db, DailyWin) - win_ids) == 1
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.status == AI_RUN_STATUS_SUCCEEDED
    assert run.provider == "fake"
    assert run.model == "fake-model"
    assert run.input_tokens == 11
    assert run.output_tokens == 22
    assert run.total_tokens == 33
    assert run.latency_ms == 5
    assert run.provider_request_id == "fake-request"
    assert run.error_code is None
    assert run.prompt_version == "daily_win_generator_v3"


def test_primary_skill_mismatch_is_rejected(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="writing.organization")
    )
    try:
        generate_demo_daily_win(demo_db, gateway)
        raise AssertionError("expected rejection")
    except Exception as exc:
        assert getattr(exc, "code", None) == "primary_goal_mismatch"

    assert _ids(demo_db, DailyWin) == win_ids
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.status == AI_RUN_STATUS_REJECTED
    assert run.error_code == "primary_goal_mismatch"


def test_unknown_skill_code_is_rejected(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="invented.skill")
    )
    try:
        generate_demo_daily_win(demo_db, gateway)
        raise AssertionError("expected rejection")
    except Exception as exc:
        assert getattr(exc, "code", None) == "unknown_skill"

    assert _ids(demo_db, DailyWin) == win_ids
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.status == AI_RUN_STATUS_REJECTED
    assert run.error_code == "unknown_skill"


def test_unsafe_output_is_rejected_without_persisting_daily_win(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(
            extra_step="Use scissors to cut cardboard",
            safety_flags=[],
        )
    )
    try:
        generate_demo_daily_win(demo_db, gateway)
        raise AssertionError("expected rejection")
    except Exception as exc:
        assert getattr(exc, "code", None) == "unsafe_content"

    assert _ids(demo_db, DailyWin) == win_ids
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.status == AI_RUN_STATUS_REJECTED
    assert run.error_code == "unsafe_content"


def test_ai_run_records_controlled_provider_failure(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway(error=ModelGatewayConfigurationError())
    try:
        generate_demo_daily_win(demo_db, gateway)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert getattr(exc, "code", None) == "configuration_error"

    assert _ids(demo_db, DailyWin) == win_ids
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.status == "failed"
    assert run.error_code == "configuration_error"


def test_ai_runs_have_no_raw_prompt_or_profile_fields() -> None:
    columns = {column.name for column in inspect(AiRun).mapper.columns}
    forbidden = {
        "prompt",
        "system_prompt",
        "user_prompt",
        "raw_prompt",
        "raw_response",
        "model_response",
        "completion",
        "profile",
        "child_profile",
        "api_key",
    }
    assert forbidden.isdisjoint(columns)


def test_demo_daily_win_endpoints_absent_in_production() -> None:
    application = create_app(Settings(app_env="production"))
    paths = _route_paths(application)
    assert "/api/v1/demo/daily-wins/generate" not in paths
    assert "/api/v1/demo/daily-wins/latest" not in paths
    assert "/api/v1/demo/daily-wins/{daily_win_id}/feedback" not in paths
    assert "/api/v1/demo/reset" not in paths
    client = TestClient(application)
    assert client.post("/api/v1/demo/daily-wins/generate").status_code == 404
    assert client.get("/api/v1/demo/daily-wins/latest").status_code == 404
    assert client.post(
        "/api/v1/demo/daily-wins/00000000-0000-0000-0000-000000000000/feedback",
        json=_feedback_payload(),
    ).status_code == 404
    assert client.post("/api/v1/demo/reset").status_code == 404


def test_get_latest_returns_persisted_daily_win(demo_db) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client = TestClient(application)

    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200
    latest = client.get("/api/v1/demo/daily-wins/latest")
    assert latest.status_code == 200
    body = latest.json()
    assert body["id"] == generated.json()["id"]
    assert body["primary_skill_code"] == "growth.persistence"
    assert body["has_feedback"] is False
    assert "household_id" not in body
    assert "ai_run_id" not in body
    assert "context_manifest" not in body


def test_development_failure_includes_sanitized_error_code(demo_db) -> None:
    win_ids = _ids(demo_db, DailyWin)
    run_ids = _ids(demo_db, AiRun)
    gateway = FakeModelGateway(error=ModelGatewayError("insufficient_quota"))
    application = _development_app(demo_db, gateway)
    client = TestClient(application)

    response = client.post("/api/v1/demo/daily-wins/generate")

    assert response.status_code == 502
    body = response.json()
    assert body["detail"] == "Daily Win could not be created. Please try again."
    assert body["error_code"] == "insufficient_quota"
    assert set(body) == {"detail", "error_code"}
    assert "exceeded" not in response.text
    assert "platform.openai.com" not in response.text
    run = _new_row(demo_db, AiRun, run_ids)
    assert run.error_code == "insufficient_quota"
    assert _ids(demo_db, DailyWin) == win_ids


def test_production_failure_omits_error_code() -> None:
    from daily_win_api.api.errors import SanitizedClientError, generation_error_payload
    from daily_win_api.domains.daily_wins.schemas import CLIENT_GENERATION_FAILED

    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "insufficient_quota",
        include_error_code=False,
    )
    assert payload == {"detail": CLIENT_GENERATION_FAILED}
    assert "error_code" not in payload

    application = create_app(Settings(app_env="production"))

    @application.get("/_test/generation-error")
    def raise_generation_error():
        raise SanitizedClientError(
            502, CLIENT_GENERATION_FAILED, "insufficient_quota"
        )

    client = TestClient(application)
    missing = client.post("/api/v1/demo/daily-wins/generate")
    assert missing.status_code == 404
    assert "error_code" not in missing.json()

    response = client.get("/_test/generation-error")
    assert response.status_code == 502
    body = response.json()
    assert body == {"detail": CLIENT_GENERATION_FAILED}
    assert "error_code" not in body
    assert "insufficient_quota" not in response.text


def test_unsafe_http_failure_includes_error_code_without_raw_steps(demo_db) -> None:
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(
            extra_step="Use scissors to cut cardboard",
            safety_flags=[],
        )
    )
    application = _development_app(demo_db, gateway)
    client = TestClient(application)

    response = client.post("/api/v1/demo/daily-wins/generate")

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Daily Win could not be created. Please try again."
    assert body["error_code"] == "unsafe_content"
    assert "scissors" not in response.text
    assert "cardboard" not in response.text


def _feedback_payload() -> dict[str, str]:
    return {
        "difficulty": "about_right",
        "engagement": "high",
        "completion": "completed",
        "setback_response": "continued_after_prompt",
    }
