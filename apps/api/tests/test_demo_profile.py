from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from daily_win_api.core.config import Settings
from daily_win_api.db.session import get_db
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.learning.models import ChildGoal, Skill
from daily_win_api.main import create_app
from tests.demo_client import DemoClient


def _development_app(db_session):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    return application


def _development_client(db_session) -> DemoClient:
    return DemoClient(_development_app(db_session))


def _route_paths(application) -> set[str]:
    return set(application.openapi().get("paths", {}))


def test_demo_child_profile_returns_seeded_hayes(db_session) -> None:
    application = _development_app(db_session)
    client = DemoClient(application)
    client.setup_hayes()
    response = client.get("/api/v1/demo/child-profile")

    assert response.status_code == 200
    body = response.json()
    assert "/api/v1/demo/child-profile" in _route_paths(application)

    assert body["child"]["nickname"] == "Hayes"
    assert body["tester_fingerprint"]
    assert len(body["tester_fingerprint"]) == 6
    assert body["tester_fingerprint"] == body["tester_fingerprint"].upper()
    assert "household_id" not in body["child"]
    assert "household_id" not in body["baseline"]

    child = db_session.get(Child, UUID(body["child"]["id"]))
    assert child is not None
    baseline = db_session.scalars(
        select(ChildBaseline)
        .where(ChildBaseline.child_id == child.id)
        .order_by(ChildBaseline.recorded_at.desc())
    ).first()
    assert baseline is not None
    goal_rows = db_session.execute(
        select(ChildGoal, Skill)
        .join(Skill, Skill.id == ChildGoal.skill_id)
        .where(
            ChildGoal.child_id == child.id,
            ChildGoal.household_id == child.household_id,
            ChildGoal.active.is_(True),
        )
        .order_by(ChildGoal.priority.asc())
    ).all()

    assert body["baseline"]["age_years"] == baseline.age_years
    assert body["baseline"]["grade"] == baseline.grade
    assert body["baseline"]["interests"] == baseline.interests
    assert body["baseline"]["strengths"] == baseline.strengths
    assert body["baseline"]["current_difficulties"] == baseline.current_difficulties
    assert body["baseline"]["motivators"] == baseline.motivators
    assert body["baseline"]["response_to_difficulty"] == baseline.response_to_difficulty
    assert (
        body["baseline"]["preferred_activity_minutes"]
        == baseline.preferred_activity_minutes
    )
    assert [goal["priority"] for goal in body["goals"]] == [1, 2, 3]
    assert [goal["skill_code"] for goal in body["goals"]] == [
        skill.code for _, skill in goal_rows
    ]
    assert [goal["display_name"] for goal in body["goals"]] == [
        skill.display_name for _, skill in goal_rows
    ]
    assert [goal["domain"] for goal in body["goals"]] == [
        skill.domain for _, skill in goal_rows
    ]


def test_demo_child_profile_reads_live_database_values(db_session) -> None:
    client = _development_client(db_session)
    client.setup_hayes()
    first = client.get("/api/v1/demo/child-profile")
    assert first.status_code == 200
    child = db_session.get(Child, UUID(first.json()["child"]["id"]))
    assert child is not None
    child.nickname = "SyntheticProbe"
    baseline = db_session.scalars(
        select(ChildBaseline)
        .where(ChildBaseline.child_id == child.id)
        .order_by(ChildBaseline.recorded_at.desc())
    ).first()
    assert baseline is not None
    baseline.preferred_activity_minutes = 17
    db_session.flush()

    response = client.get("/api/v1/demo/child-profile")

    assert response.status_code == 200
    body = response.json()
    assert body["child"]["nickname"] == "SyntheticProbe"
    assert body["baseline"]["preferred_activity_minutes"] == 17


def test_demo_child_profile_unavailable_returns_controlled_error(db_session) -> None:
    client = _development_client(db_session)
    client.setup_hayes()
    first = client.get("/api/v1/demo/child-profile")
    assert first.status_code == 200
    child_id = UUID(first.json()["child"]["id"])
    db_session.execute(delete(ChildBaseline).where(ChildBaseline.child_id == child_id))
    db_session.flush()

    response = client.get("/api/v1/demo/child-profile")

    assert response.status_code == 404
    assert response.json() == {"detail": "Demo child profile is not available."}
    assert "hayes" not in response.text.lower()


def test_demo_routes_require_session_header(db_session) -> None:
    client = TestClient(_development_app(db_session))
    response = client.get("/api/v1/demo/child-profile")
    assert response.status_code == 400
    assert response.json()["error_code"] == "demo_unavailable"


def test_demo_child_profile_route_absent_in_production() -> None:
    application = create_app(Settings(app_env="production"))
    client = TestClient(application)

    assert "/api/v1/demo/child-profile" not in _route_paths(application)
    response = client.get("/api/v1/demo/child-profile")
    assert response.status_code == 404
