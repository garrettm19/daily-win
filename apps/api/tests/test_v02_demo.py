from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import FakeModelGateway, valid_daily_win_draft
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.db.session import get_db
from daily_win_api.dev.presets import (
    FORBIDDEN_ONBOARDING_FIELDS,
    HAYES_PROFILE,
    V02_COLLECTION_FIELDS,
)
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.learning.models import LearnerSkillState, LearningEvent
from daily_win_api.main import create_app
from tests.demo_client import DEMO_SESSION_A, DEMO_SESSION_B, DemoClient

CONTINUED_JSON = {
    "difficulty": "about_right",
    "engagement": "high",
    "completion": "completed",
    "setback_response": "continued_after_prompt",
}

NOVA_WRITE = {
    "nickname": "Nova",
    "age_years": 8,
    "grade": "3",
    "interests": ["space", "drawing"],
    "strengths": ["reading"],
    "current_difficulties": ["organizing writing"],
    "response_to_difficulty": "asks for help quickly",
    "goal_codes": ["writing.organization", "growth.persistence"],
    "primary_goal_code": "writing.organization",
    "motivators": ["stories/imagination", "choice"],
    "preferred_activity_minutes": 20,
}

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _count(session, model, child_id) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(model).where(model.child_id == child_id)
        )
        or 0
    )


def _route_paths(application) -> set[str]:
    return set(application.openapi().get("paths", {}))


def test_new_session_begins_unconfigured(demo_db) -> None:
    client = DemoClient(_development_app(demo_db))
    session = client.get("/api/v1/demo/session")
    assert session.status_code == 200
    body = session.json()
    assert body["status"] == "new"
    assert body["profile"] is None
    assert DEMO_SESSION_A not in str(body)
    profile = client.get("/api/v1/demo/child-profile")
    assert profile.status_code == 409
    assert profile.json()["error_code"] == "setup_required"
    generate = client.post("/api/v1/demo/daily-wins/generate")
    assert generate.status_code == 409
    assert generate.json()["error_code"] == "setup_required"


def test_hayes_preset_setup(demo_db) -> None:
    client = DemoClient(_development_app(demo_db))
    created = client.setup_hayes()
    body = created.json()
    assert body["child"]["nickname"] == "Hayes"
    assert body["baseline"]["age_years"] == 7
    assert body["baseline"]["grade"] == "1"
    assert list(body["baseline"]["interests"]) == list(HAYES_PROFILE.interests)
    assert "Dad" not in str(body["baseline"]["motivators"])
    assert body["goals"][0]["skill_code"] == "growth.persistence"
    session = client.get("/api/v1/demo/session")
    assert session.json()["status"] == "ready"
    assert session.json()["profile_source"] == "hayes"
    again = client.post("/api/v1/demo/setup/hayes")
    assert again.status_code == 409
    assert again.json()["error_code"] == "already_configured"


def test_custom_profile_setup_and_validation(demo_db) -> None:
    client = DemoClient(_development_app(demo_db))
    created = client.setup_profile(NOVA_WRITE)
    body = created.json()
    assert body["child"]["nickname"] == "Nova"
    assert body["baseline"]["age_years"] == 8
    assert [goal["skill_code"] for goal in body["goals"]] == [
        "writing.organization",
        "growth.persistence",
    ]
    invalid_age = dict(NOVA_WRITE, nickname="Orion", age_years=4)
    age_response = client.post("/api/v1/demo/setup/profile", json=invalid_age)
    assert age_response.status_code == 422
    too_many_goals = dict(
        NOVA_WRITE,
        nickname="Orion",
        goal_codes=[
            "writing.organization",
            "growth.persistence",
            "math.addition",
            "reading.fluency",
        ],
        primary_goal_code="writing.organization",
    )
    many = client.post("/api/v1/demo/setup/profile", json=too_many_goals)
    assert many.status_code == 422
    duplicates = dict(
        NOVA_WRITE,
        nickname="Orion",
        goal_codes=["writing.organization", "writing.organization"],
        primary_goal_code="writing.organization",
    )
    assert client.post("/api/v1/demo/setup/profile", json=duplicates).status_code == 422
    missing_primary = dict(NOVA_WRITE, nickname="Orion")
    missing_primary.pop("primary_goal_code")
    assert (
        client.post("/api/v1/demo/setup/profile", json=missing_primary).status_code
        == 422
    )
    for field in FORBIDDEN_ONBOARDING_FIELDS:
        extra = dict(NOVA_WRITE, nickname="Orion")
        extra[field] = "not-allowed"
        response = client.post("/api/v1/demo/setup/profile", json=extra)
        assert response.status_code == 422, field


def test_custom_profile_context_generation(demo_db) -> None:
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="writing.organization")
    )
    client = DemoClient(_development_app(demo_db, gateway))
    client.setup_profile(NOVA_WRITE)
    created = client.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    context = gateway.calls[-1]
    dumped = context.model_dump()
    assert context.nickname == "Nova"
    assert context.parent_reported_baseline.age_years == 8
    assert context.parent_reported_baseline.interests == ["space", "drawing"]
    assert context.parent_reported_baseline.strengths == ["reading"]
    assert context.parent_reported_baseline.current_difficulties == [
        "organizing writing"
    ]
    assert context.instruction_plan.primary_skill_code == (
        "writing.sentences.complete_sentence"
    )
    assert "child_id" not in dumped
    assert "household_id" not in dumped
    assert "session_hash" not in dumped
    assert DEMO_SESSION_A not in str(dumped)


def test_profile_edits_affect_future_generation_only(demo_db) -> None:
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="writing.organization")
    )
    client = DemoClient(_development_app(demo_db, gateway))
    client.setup_profile(NOVA_WRITE)
    created = client.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    win_id = created.json()["id"]
    win_before = created.json()
    feedback = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )
    assert feedback.status_code == 200
    child_id = UUID(client.get("/api/v1/demo/child-profile").json()["child"]["id"])
    event_payloads = [
        (row.id, dict(row.payload))
        for row in demo_db.scalars(
            select(LearningEvent).where(LearningEvent.child_id == child_id)
        )
    ]
    baseline_ids = list(
        demo_db.scalars(
            select(ChildBaseline.id).where(ChildBaseline.child_id == child_id)
        )
    )
    update = {
        "interests": ["space", "drawing"],
        "strengths": ["reading"],
        "current_difficulties": ["organizing writing"],
        "response_to_difficulty": "asks for help quickly",
        "goal_codes": ["growth.persistence", "writing.organization"],
        "primary_goal_code": "growth.persistence",
        "motivators": ["stories/imagination", "choice"],
        "preferred_activity_minutes": 20,
    }
    patched = client.patch("/api/v1/demo/profile", json=update)
    assert patched.status_code == 200
    assert patched.json()["goals"][0]["skill_code"] == "growth.persistence"
    historical = client.get(f"/api/v1/demo/daily-wins/{win_id}")
    assert historical.status_code == 200
    assert historical.json()["title"] == win_before["title"]
    assert historical.json()["content"] == win_before["content"]
    assert historical.json()["primary_skill_code"] == (
        "writing.sentences.complete_sentence"
    )
    after_events = [
        (row.id, dict(row.payload))
        for row in demo_db.scalars(
            select(LearningEvent).where(LearningEvent.child_id == child_id)
        )
    ]
    assert after_events == event_payloads
    later_baselines = list(
        demo_db.scalars(
            select(ChildBaseline.id).where(ChildBaseline.child_id == child_id)
        )
    )
    assert len(later_baselines) == len(baseline_ids) + 1
    gateway.draft = valid_daily_win_draft()
    nxt = client.post("/api/v1/demo/daily-wins/generate")
    assert nxt.status_code == 200
    later_plan = gateway.calls[-1].instruction_plan
    assert later_plan.primary_skill_code.startswith("writing.")
    assert later_plan.growth_target_code == "growth.persistence"
    assert gateway.calls[-1].nickname == "Nova"


def test_progress_is_cautious_and_evidence_based(demo_db) -> None:
    gateway = FakeModelGateway()
    client = DemoClient(_development_app(demo_db, gateway))
    client.setup_hayes()
    empty = client.get("/api/v1/demo/progress")
    assert empty.status_code == 200
    first_goal = empty.json()["goals"][0]
    assert first_goal["still_learning"] is True
    assert "few more Daily Wins" in (first_goal["still_learning_message"] or "")
    assert first_goal["recent_pattern"] is None
    dumped = str(empty.json())
    assert "%" not in dumped
    assert "mastery" not in dumped.lower()
    created = client.post("/api/v1/demo/daily-wins/generate")
    feedback = client.post(
        f"/api/v1/demo/daily-wins/{created.json()['id']}/feedback",
        json=CONTINUED_JSON,
    )
    assert feedback.status_code == 200
    progress = client.get("/api/v1/demo/progress")
    body = progress.json()
    persistence = body["goals"][0]
    assert persistence["evidence_count"] == 1
    assert persistence["evidence_label"] == "1 observation"
    assert persistence["still_learning"] is True
    assert persistence["recent_pattern"] is None
    assert "Hayes" in (persistence["latest_observation"] or "")
    assert body["recent_observations"]
    assert "additional_note" not in str(body)
    assert "%" not in str(body)


def test_history_order_ownership_and_no_resubmit(demo_db) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client_a = DemoClient(application, DEMO_SESSION_A)
    client_b = DemoClient(application, DEMO_SESSION_B)
    client_a.setup_hayes()
    client_b.setup_hayes()
    first = client_a.post("/api/v1/demo/daily-wins/generate")
    assert first.status_code == 200
    client_a.post(
        f"/api/v1/demo/daily-wins/{first.json()['id']}/feedback", json=CONTINUED_JSON
    )
    second = client_a.post("/api/v1/demo/daily-wins/generate")
    assert second.status_code == 200
    history = client_a.get("/api/v1/demo/daily-wins")
    ids = [item["id"] for item in history.json()]
    assert ids == [second.json()["id"], first.json()["id"]]
    historical = client_a.get(f"/api/v1/demo/daily-wins/{first.json()['id']}")
    assert historical.status_code == 200
    assert historical.json()["has_feedback"] is True
    resubmit = client_a.post(
        f"/api/v1/demo/daily-wins/{first.json()['id']}/feedback", json=CONTINUED_JSON
    )
    assert resubmit.status_code == 409
    foreign = client_b.get(f"/api/v1/demo/daily-wins/{first.json()['id']}")
    assert foreign.status_code == 404
    assert "not available" in foreign.json()["detail"].lower()
    missing = client_a.get(
        "/api/v1/demo/daily-wins/00000000-0000-0000-0000-000000000000"
    )
    assert missing.status_code == 404


def test_two_tester_isolation_resets_and_progress(demo_db) -> None:
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="writing.organization")
    )
    application = _development_app(demo_db, gateway)
    client_a = DemoClient(application, DEMO_SESSION_A)
    client_b = DemoClient(application, DEMO_SESSION_B)

    client_a.setup_hayes()
    gateway.draft = valid_daily_win_draft()
    win_a = client_a.post("/api/v1/demo/daily-wins/generate")
    assert win_a.status_code == 200
    feedback_a = client_a.post(
        f"/api/v1/demo/daily-wins/{win_a.json()['id']}/feedback", json=CONTINUED_JSON
    )
    assert feedback_a.status_code == 200
    progress_a = client_a.get("/api/v1/demo/progress")
    assert progress_a.json()["goals"][0]["evidence_count"] == 1
    assert progress_a.json()["nickname"] == "Hayes"

    client_b.setup_profile(NOVA_WRITE)
    gateway.draft = valid_daily_win_draft(primary_skill_code="writing.organization")
    win_b = client_b.post("/api/v1/demo/daily-wins/generate")
    assert win_b.status_code == 200
    context = gateway.calls[-1]
    assert context.nickname == "Nova"
    assert context.instruction_plan.primary_skill_code == (
        "writing.sentences.complete_sentence"
    )
    client_b.post(
        f"/api/v1/demo/daily-wins/{win_b.json()['id']}/feedback", json=CONTINUED_JSON
    )
    progress_b = client_b.get("/api/v1/demo/progress")
    assert progress_b.json()["nickname"] == "Nova"
    assert "Hayes" not in str(progress_b.json()["recent_observations"])
    child_a = UUID(client_a.get("/api/v1/demo/child-profile").json()["child"]["id"])
    child_b = UUID(client_b.get("/api/v1/demo/child-profile").json()["child"]["id"])
    assert child_a != child_b

    reset_a = client_a.post("/api/v1/demo/reset/activity")
    assert reset_a.status_code == 200
    assert client_a.get("/api/v1/demo/session").json()["status"] == "ready"
    assert client_a.get("/api/v1/demo/child-profile").json()["child"]["nickname"] == (
        "Hayes"
    )
    assert client_a.get("/api/v1/demo/daily-wins/latest").status_code == 404
    assert _count(demo_db, DailyWin, child_a) == 0
    assert _count(demo_db, LearningEvent, child_a) == 0
    assert _count(demo_db, LearnerSkillState, child_a) == 0
    assert _count(demo_db, DailyWin, child_b) == 1
    assert client_b.get("/api/v1/demo/child-profile").json()["child"]["nickname"] == (
        "Nova"
    )

    restart_b = client_b.post("/api/v1/demo/reset/session")
    assert restart_b.status_code == 200
    assert client_b.get("/api/v1/demo/session").json()["status"] == "new"
    assert client_b.get("/api/v1/demo/child-profile").status_code == 409
    assert demo_db.get(Child, child_b) is None
    assert client_a.get("/api/v1/demo/session").json()["status"] == "ready"
    assert client_a.get("/api/v1/demo/child-profile").json()["child"]["nickname"] == (
        "Hayes"
    )


def test_production_still_has_no_demo_routes() -> None:
    application = create_app(Settings(app_env="production"))
    paths = _route_paths(application)
    for path in (
        "/api/v1/demo/session",
        "/api/v1/demo/setup/hayes",
        "/api/v1/demo/setup/profile",
        "/api/v1/demo/profile",
        "/api/v1/demo/progress",
        "/api/v1/demo/daily-wins",
        "/api/v1/demo/daily-wins/{daily_win_id}",
        "/api/v1/demo/reset/activity",
        "/api/v1/demo/reset/session",
    ):
        assert path not in paths
    client = TestClient(application)
    assert client.get("/api/v1/demo/session").status_code == 404
    assert client.post("/api/v1/demo/setup/hayes").status_code == 404
    assert client.get("/api/v1/demo/progress").status_code == 404


def test_data_lifecycle_docs_match_v02_fields() -> None:
    text = (DOCS_DIR / "data-lifecycle.md").read_text(encoding="utf-8")
    for field in V02_COLLECTION_FIELDS:
        assert field in text, field
    for field in FORBIDDEN_ONBOARDING_FIELDS:
        assert field in text, field
    assert "V0.2" in text
    assert "made-up" in text.lower() or "synthetic" in text.lower()
