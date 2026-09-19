from uuid import UUID

from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.db.session import get_db
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.learning.models import LearnerSkillState, LearningEvent
from daily_win_api.main import create_app
from tests.demo_client import DEMO_SESSION_A, DEMO_SESSION_B, DemoClient

CONTINUED_JSON = {
    "difficulty": "about_right",
    "engagement": "high",
    "completion": "completed",
    "setback_response": "continued_after_prompt",
}


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


def test_demo_sessions_are_isolated_and_reset_is_scoped(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    client_a = DemoClient(application, DEMO_SESSION_A)
    client_b = DemoClient(application, DEMO_SESSION_B)
    client_a.setup_hayes()
    client_b.setup_hayes()

    profile_a = client_a.get("/api/v1/demo/child-profile")
    profile_b = client_b.get("/api/v1/demo/child-profile")
    assert profile_a.status_code == 200
    assert profile_b.status_code == 200
    body_a = profile_a.json()
    body_b = profile_b.json()
    assert body_a["child"]["nickname"] == "Hayes"
    assert body_b["child"]["nickname"] == "Hayes"
    assert body_a["child"]["id"] != body_b["child"]["id"]
    assert body_a["tester_fingerprint"] != body_b["tester_fingerprint"]
    assert DEMO_SESSION_A not in str(body_a)
    assert DEMO_SESSION_B not in str(body_b)

    created_a = client_a.post("/api/v1/demo/daily-wins/generate")
    assert created_a.status_code == 200
    feedback_a = client_a.post(
        f"/api/v1/demo/daily-wins/{created_a.json()['id']}/feedback",
        json=CONTINUED_JSON,
    )
    assert feedback_a.status_code == 200
    assert feedback_a.json()["learner_state"]["evidence_count"] >= 1

    latest_b = client_b.get("/api/v1/demo/daily-wins/latest")
    assert latest_b.status_code == 404
    child_b = UUID(body_b["child"]["id"])
    assert _count(demo_db, DailyWin, child_b) == 0
    assert _count(demo_db, DailyWinFeedback, child_b) == 0
    assert _count(demo_db, LearningEvent, child_b) == 0
    assert _count(demo_db, LearnerSkillState, child_b) == 0

    created_b = client_b.post("/api/v1/demo/daily-wins/generate")
    assert created_b.status_code == 200
    win_b_id = created_b.json()["id"]

    reset_a = client_a.post("/api/v1/demo/reset")
    assert reset_a.status_code == 200
    assert client_a.get("/api/v1/demo/daily-wins/latest").status_code == 404
    child_a = UUID(body_a["child"]["id"])
    assert _count(demo_db, DailyWin, child_a) == 0
    assert _count(demo_db, DailyWinFeedback, child_a) == 0
    assert _count(demo_db, LearningEvent, child_a) == 0
    assert _count(demo_db, LearnerSkillState, child_a) == 0

    latest_b_after = client_b.get("/api/v1/demo/daily-wins/latest")
    assert latest_b_after.status_code == 200
    assert latest_b_after.json()["id"] == win_b_id
    assert _count(demo_db, DailyWin, child_b) == 1
