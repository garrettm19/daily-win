from uuid import UUID

from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.db.session import get_db
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.main import create_app
from tests.demo_client import DEMO_SESSION_A, DEMO_SESSION_B, DemoClient


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def test_latest_win_is_discoverable_after_generate(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    http = DemoClient(application)
    http.setup_hayes()
    created = http.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    latest = http.get("/api/v1/demo/daily-wins/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == created.json()["id"]
    assert latest.json()["has_feedback"] is False


def test_generate_retry_does_not_duplicate_unreflected_win(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    http = DemoClient(application)
    http.setup_hayes()
    first = http.post("/api/v1/demo/daily-wins/generate")
    retry = http.post("/api/v1/demo/daily-wins/generate")
    latest = http.get("/api/v1/demo/daily-wins/latest")
    assert first.status_code == 200
    assert retry.status_code == 409
    assert retry.json()["error_code"] == "feedback_required"
    assert latest.status_code == 200
    assert latest.json()["id"] == first.json()["id"]
    child_id = UUID(http.get("/api/v1/demo/child-profile").json()["child"]["id"])
    assert (
        demo_db.scalar(
            select(func.count())
            .select_from(DailyWin)
            .where(DailyWin.child_id == child_id)
        )
        == 1
    )


def test_two_sessions_stay_isolated_after_activity_reset(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    mason = DemoClient(application, DEMO_SESSION_A)
    cory = DemoClient(application, DEMO_SESSION_B)
    mason.setup_hayes()
    cory.setup_hayes()
    mason_session = mason.get("/api/v1/demo/session").json()
    cory_session = cory.get("/api/v1/demo/session").json()
    assert mason_session["tester_fingerprint"] != cory_session["tester_fingerprint"]
    created = mason.post("/api/v1/demo/daily-wins/generate")
    cory_win = cory.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    assert cory_win.status_code == 200
    reset = mason.post("/api/v1/demo/reset/activity")
    assert reset.status_code == 200
    assert cory.get("/api/v1/demo/session").json()["status"] == "ready"
    assert mason.get("/api/v1/demo/daily-wins/latest").status_code == 404
    cory_latest = cory.get("/api/v1/demo/daily-wins/latest")
    assert cory_latest.status_code == 200
    assert cory_latest.json()["id"] == cory_win.json()["id"]
    assert cory.get("/api/v1/demo/child-profile").json()["child"]["nickname"] == "Hayes"
