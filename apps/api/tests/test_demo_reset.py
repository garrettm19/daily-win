from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import (
    FakeModelGateway,
    adaptive_daily_win_draft,
    valid_daily_win_draft,
)
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import (
    DEMO_CHILD_ID,
    DEMO_HOUSEHOLD_ID,
    get_demo_child,
    skill_id_for_code,
)
from daily_win_api.db.session import get_db
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.dev.seed import HAYES_GOAL_CODES, seed_development_data
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    DailyWinFeedbackCreate,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.households.models import Household
from daily_win_api.domains.learning.models import (
    ChildGoal,
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
    Skill,
)
from daily_win_api.main import create_app

CONTINUED_PAYLOAD = DailyWinFeedbackCreate(
    difficulty="about_right",
    engagement="high",
    completion="completed",
    setback_response="continued_after_prompt",
)


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _count_for_child(session, model) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(model)
            .where(model.child_id == DEMO_CHILD_ID)
        )
        or 0
    )


def test_reset_removes_derived_demo_data_and_preserves_seed(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)

    skill_count_before = demo_db.scalar(select(func.count()).select_from(Skill))
    baseline_before = demo_db.scalar(
        select(ChildBaseline).where(ChildBaseline.child_id == DEMO_CHILD_ID)
    )
    assert baseline_before is not None
    baseline_snapshot = (
        baseline_before.age_years,
        baseline_before.grade,
        list(baseline_before.interests),
    )
    goals_before = demo_db.execute(
        select(ChildGoal.priority, ChildGoal.skill_id)
        .where(ChildGoal.child_id == DEMO_CHILD_ID)
        .order_by(ChildGoal.priority.asc())
    ).all()

    reset_demo_derived_data(demo_db)
    seed_development_data(demo_db)

    assert _count_for_child(demo_db, DailyWinFeedback) == 0
    assert _count_for_child(demo_db, DailyWin) == 0
    assert _count_for_child(demo_db, AiRun) == 0
    assert _count_for_child(demo_db, LearningEvent) == 0
    assert _count_for_child(demo_db, LearnerSkillState) == 0
    evidence = demo_db.scalar(
        select(func.count()).select_from(LearnerSkillStateEvidence)
    )
    assert evidence == 0

    child = get_demo_child(demo_db)
    assert child is not None
    assert child.nickname == "Hayes"
    household = demo_db.get(Household, DEMO_HOUSEHOLD_ID)
    assert household is not None
    baseline = demo_db.scalar(
        select(ChildBaseline).where(ChildBaseline.child_id == DEMO_CHILD_ID)
    )
    assert baseline is not None
    assert (
        baseline.age_years,
        baseline.grade,
        list(baseline.interests),
    ) == baseline_snapshot
    goals_after = demo_db.execute(
        select(ChildGoal.priority, ChildGoal.skill_id)
        .where(ChildGoal.child_id == DEMO_CHILD_ID)
        .order_by(ChildGoal.priority.asc())
    ).all()
    assert goals_after == goals_before
    goal_codes = [
        demo_db.get(Skill, skill_id).code
        for _priority, skill_id in goals_after
    ]
    assert goal_codes == list(HAYES_GOAL_CODES)
    assert demo_db.scalar(select(func.count()).select_from(Skill)) == skill_count_before


def test_reset_cannot_affect_another_household(demo_db) -> None:
    other_win = _insert_other_household_win(demo_db)
    generate_demo_daily_win(demo_db, FakeModelGateway())
    reset_demo_derived_data(demo_db)

    remaining = demo_db.get(DailyWin, other_win.id)
    assert remaining is not None
    assert remaining.household_id != DEMO_HOUSEHOLD_ID
    assert remaining.child_id != DEMO_CHILD_ID
    assert _count_for_child(demo_db, DailyWin) == 0


def test_reset_route_absent_in_production() -> None:
    application = create_app(Settings(app_env="production"))
    paths = set(application.openapi().get("paths", {}))
    assert "/api/v1/demo/reset" not in paths
    client = TestClient(application)
    assert client.post("/api/v1/demo/reset").status_code == 404


def test_reset_http_returns_simple_success(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    application = _development_app(demo_db, FakeModelGateway())
    client = TestClient(application)
    response = client.post("/api/v1/demo/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "household_id" not in response.json()
    assert _count_for_child(demo_db, DailyWin) == 0


def test_home_states_none_pending_and_reflected(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    client = TestClient(application)

    missing = client.get("/api/v1/demo/daily-wins/latest")
    assert missing.status_code == 404

    created = client.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    assert created.json()["has_feedback"] is False
    latest = client.get("/api/v1/demo/daily-wins/latest")
    assert latest.json()["has_feedback"] is False

    feedback = client.post(
        f"/api/v1/demo/daily-wins/{created.json()['id']}/feedback",
        json=CONTINUED_PAYLOAD.model_dump(mode="json"),
    )
    assert feedback.status_code == 200
    reflected = client.get("/api/v1/demo/daily-wins/latest")
    assert reflected.json()["has_feedback"] is True


def test_reset_then_fake_gateway_adaptation_loop(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    reset_demo_derived_data(demo_db)
    seed_development_data(demo_db)

    gateway = FakeModelGateway(adaptive_draft=adaptive_daily_win_draft("Hayes"))
    first = generate_demo_daily_win(demo_db, gateway)
    assert first.content.adaptation_summary is None
    result = submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    assert result.learner_state.latest_signal == "retry_after_prompt"
    second = generate_demo_daily_win(demo_db, gateway)
    assert second.content.adaptation_summary is not None
    assert "prompt" in second.content.adaptation_summary.lower()
    assert second.title != first.title


def _insert_other_household_win(session) -> DailyWin:
    household = Household(id=uuid4(), display_name="Other Household")
    session.add(household)
    session.flush()
    child = Child(id=uuid4(), household_id=household.id, nickname="Other")
    session.add(child)
    session.flush()
    run = AiRun(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="fake",
        model="fake-model",
        prompt_version="daily_win_generator_v3",
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        status="succeeded",
        context_manifest={"synthetic": True},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    draft = valid_daily_win_draft(title="Other household win")
    win = DailyWin(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        primary_skill_id=skill_id_for_code("growth.persistence"),
        ai_run_id=run.id,
        title=draft.title,
        objective=draft.objective,
        duration_minutes=draft.duration_minutes,
        content=draft.model_dump(mode="json"),
        content_schema_version=CONTENT_SCHEMA_VERSION,
        status=DAILY_WIN_STATUS_READY,
    )
    session.add(win)
    session.flush()
    return win
