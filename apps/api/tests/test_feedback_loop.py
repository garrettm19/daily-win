from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import (
    FakeModelGateway,
    adaptive_daily_win_draft,
    valid_daily_win_draft,
)
from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.db.session import get_db
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.context import build_daily_win_context
from daily_win_api.domains.daily_wins.enums import (
    PersistenceSignal,
    SetbackResponse,
    TrendDirection,
)
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
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.projector import project_persistence_state
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_DAILY_WIN_FEEDBACK,
    EVENT_TYPE_SKILL_OBSERVATION,
    PERSISTENCE_SKILL_CODE,
    TREND_PROJECTOR_V1,
)
from daily_win_api.main import create_app

CONTINUED_PAYLOAD = DailyWinFeedbackCreate(
    difficulty="about_right",
    engagement="high",
    completion="completed",
    setback_response="continued_after_prompt",
    what_helped="A reminder to look at the plan helped Hayes choose one change.",
    additional_note="Kept it light and stopped after one retry.",
)

CONTINUED_JSON = CONTINUED_PAYLOAD.model_dump(mode="json")


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _persistence_skill(session) -> Skill:
    skill = session.scalar(select(Skill).where(Skill.code == PERSISTENCE_SKILL_CODE))
    assert skill is not None
    return skill


def test_feedback_is_persisted_correctly(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    assert child is not None
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None

    result = submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    row = demo_db.get(DailyWinFeedback, result.feedback_id)
    assert row is not None
    assert row.daily_win_id == win.id
    assert row.child_id == child.id
    assert row.household_id == child.household_id
    assert row.difficulty == "about_right"
    assert row.engagement == "high"
    assert row.completion == "completed"
    assert row.setback_response == "continued_after_prompt"
    assert row.what_helped is not None
    assert "plan" in row.what_helped
    assert row.additional_note is not None
    assert "household_id" not in result.model_dump()


def test_one_feedback_per_win_is_enforced(demo_db) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client = TestClient(application)
    win_id = client.post("/api/v1/demo/daily-wins/generate").json()["id"]

    first = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )
    second = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error_code"] == "already_submitted"
    assert "household_id" not in first.json()
    assert demo_db.scalar(select(func.count()).select_from(DailyWinFeedback)) == 1


def test_feedback_cannot_target_another_household_win(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    client = TestClient(application)
    assert client.post("/api/v1/demo/daily-wins/generate").status_code == 200
    other_win = _insert_other_household_win(demo_db)

    response = client.post(
        f"/api/v1/demo/daily-wins/{other_win.id}/feedback",
        json=CONTINUED_JSON,
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "demo_unavailable"
    assert demo_db.scalar(select(func.count()).select_from(DailyWinFeedback)) == 0


def test_categorical_feedback_creates_canonical_learning_events(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    result = submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)

    events = demo_db.scalars(
        select(LearningEvent)
        .where(LearningEvent.daily_win_feedback_id == result.feedback_id)
        .order_by(LearningEvent.created_at.asc())
    ).all()
    assert len(events) == 2
    completion, observation = events
    assert completion.event_type == EVENT_TYPE_DAILY_WIN_FEEDBACK
    assert completion.skill_id is None
    assert completion.evidence_kind == "OBSERVATION"
    assert completion.source == "PARENT"
    assert completion.payload["difficulty"] == "about_right"
    assert completion.payload["engagement"] == "high"
    assert completion.payload["completion"] == "completed"
    assert "additional_note" not in completion.payload
    assert completion.daily_win_id == win.id

    assert observation.event_type == EVENT_TYPE_SKILL_OBSERVATION
    assert observation.skill_id == win.primary_skill_id
    assert observation.payload["observation_type"] == "response_after_setback"
    assert observation.payload["signal"] == "continued_after_prompt"
    assert "plan" in str(observation.payload["what_helped"])
    assert "additional_note" not in observation.payload
    assert observation.daily_win_id == win.id
    assert observation.daily_win_feedback_id == result.feedback_id


def test_no_setback_does_not_manufacture_persistence_evidence(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    payload = CONTINUED_PAYLOAD.model_copy(
        update={
            "setback_response": SetbackResponse.NO_SETBACK_OCCURRED,
            "what_helped": None,
        }
    )
    result = submit_demo_feedback(demo_db, win.id, payload)

    observation = demo_db.scalars(
        select(LearningEvent).where(
            LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION,
            LearningEvent.daily_win_feedback_id == result.feedback_id,
        )
    ).first()
    assert observation is not None
    assert observation.payload["signal"] == "no_setback_occurred"
    assert result.learner_state.latest_signal == PersistenceSignal.NO_SIGNAL
    assert "persistent" not in result.insight.observation.lower()
    assert result.learner_state.direction == TrendDirection.INSUFFICIENT_DATA


def test_continued_after_prompt_maps_to_retry_after_prompt(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    result = submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    assert result.learner_state.skill_code == PERSISTENCE_SKILL_CODE
    assert result.learner_state.latest_signal == "retry_after_prompt"
    assert result.learner_state.direction == "insufficient_data"
    assert result.learner_state.evidence_count == 1
    assert result.insight.observation == (
        "Hayes returned to the challenge after a prompt."
    )
    assert "a little more time" in result.insight.next_adjustment


def test_state_links_to_exact_source_event(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    result = submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    observation = demo_db.scalars(
        select(LearningEvent).where(
            LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION,
            LearningEvent.daily_win_feedback_id == result.feedback_id,
        )
    ).one()
    child = get_demo_child(demo_db)
    assert child is not None
    state = demo_db.scalars(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id == _persistence_skill(demo_db).id,
        )
    ).one()
    links = demo_db.scalars(
        select(LearnerSkillStateEvidence).where(
            LearnerSkillStateEvidence.learner_skill_state_id == state.id
        )
    ).all()
    assert [link.learning_event_id for link in links] == [observation.id]
    assert state.algorithm_version == TREND_PROJECTOR_V1
    assert state.confidence is None


def test_state_rebuilds_deterministically_from_events(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    assert child is not None
    first = project_persistence_state(
        demo_db,
        household_id=child.household_id,
        child_id=child.id,
        skill=_persistence_skill(demo_db),
    )
    snapshot = dict(first.state)
    first.state = {"latest_signal": "independent_retry", "tampered": True}
    rebuilt = project_persistence_state(
        demo_db,
        household_id=child.household_id,
        child_id=child.id,
        skill=_persistence_skill(demo_db),
    )
    assert rebuilt.state == snapshot
    assert rebuilt.state["latest_signal"] == "retry_after_prompt"
    assert "tampered" not in rebuilt.state


def test_fewer_than_three_observations_is_insufficient_data(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    result = submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    assert result.learner_state.direction == "insufficient_data"
    child = get_demo_child(demo_db)
    assert child is not None
    state = project_persistence_state(
        demo_db,
        household_id=child.household_id,
        child_id=child.id,
    )
    assert state.state["direction"] == "insufficient_data"


def test_context_builder_includes_adaptation_directive(demo_db) -> None:
    child = get_demo_child(demo_db)
    assert child is not None
    context, _manifest = build_daily_win_context(demo_db, child)
    assert context.adaptation_directive is not None
    assert context.adaptation_directive.skill_code == PERSISTENCE_SKILL_CODE
    assert context.adaptation_directive.latest_signal == "no_signal"
    assert "child_id" not in context.model_dump()
    assert "household_id" not in context.model_dump()


def test_generator_refuses_second_win_before_reflection(demo_db) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client = TestClient(application)
    first = client.post("/api/v1/demo/daily-wins/generate")
    second = client.post("/api/v1/demo/daily-wins/generate")
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error_code"] == "feedback_required"
    assert _count(demo_db, DailyWin) == 1


def test_generation_succeeds_after_reflection(demo_db) -> None:
    gateway = FakeModelGateway(adaptive_draft=adaptive_daily_win_draft("Hayes"))
    application = _development_app(demo_db, gateway)
    client = TestClient(application)
    first = client.post("/api/v1/demo/daily-wins/generate")
    win_id = first.json()["id"]
    feedback = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )
    second = client.post("/api/v1/demo/daily-wins/generate")
    assert feedback.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] != win_id
    assert second.json()["has_feedback"] is False


def test_adaptive_fake_win_includes_adaptation_summary(demo_db) -> None:
    draft = adaptive_daily_win_draft("Hayes")
    assert draft.adaptation_summary is not None
    assert "strong persistence" not in draft.adaptation_summary.lower()
    generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.scalars(
        select(DailyWin).order_by(DailyWin.created_at.desc())
    ).first()
    assert win is not None
    submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    second = generate_demo_daily_win(
        demo_db,
        FakeModelGateway(adaptive_draft=draft),
    )
    assert second.content.adaptation_summary == draft.adaptation_summary
    assert "tower" not in second.title.lower()


def test_old_v1_daily_win_content_still_deserializes() -> None:
    payload = valid_daily_win_draft().model_dump(mode="json")
    payload.pop("adaptation_summary", None)
    loaded = DailyWinDraft.model_validate(payload)
    assert loaded.adaptation_summary is None
    assert loaded.title == payload["title"]


def test_feedback_http_does_not_expose_household_ids(demo_db) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client = TestClient(application)
    win_id = client.post("/api/v1/demo/daily-wins/generate").json()["id"]
    response = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )
    body = response.json()
    assert response.status_code == 200
    dumped = str(body)
    child = get_demo_child(demo_db)
    assert child is not None
    assert "household_id" not in body
    assert str(child.household_id) not in dumped
    assert set(body) == {"feedback_id", "insight", "learner_state"}


def test_transaction_rollback_prevents_partial_feedback_state(
    demo_db, monkeypatch
) -> None:
    gateway = FakeModelGateway()
    application = _development_app(demo_db, gateway)
    client = TestClient(application)
    win_id = client.post("/api/v1/demo/daily-wins/generate").json()["id"]
    before_feedback = _count(demo_db, DailyWinFeedback)
    before_events = _count(demo_db, LearningEvent)

    def boom(*_args, **_kwargs):
        raise RuntimeError("induced failure")

    monkeypatch.setattr(
        "daily_win_api.domains.daily_wins.feedback.project_persistence_state",
        boom,
    )
    response = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback", json=CONTINUED_JSON
    )
    assert response.status_code == 500
    assert response.json()["error_code"] == "provider_error"
    assert _count(demo_db, DailyWinFeedback) == before_feedback
    assert _count(demo_db, LearningEvent) == before_events
    child = get_demo_child(demo_db)
    assert child is not None
    state = demo_db.scalars(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id == _persistence_skill(demo_db).id,
        )
    ).first()
    assert state is None or state.state.get("latest_signal") != "retry_after_prompt"


def test_feedback_loop_end_to_end_with_fake_gateway(demo_db) -> None:
    gateway = FakeModelGateway(adaptive_draft=adaptive_daily_win_draft("Hayes"))
    first = generate_demo_daily_win(demo_db, gateway)
    assert first.content.adaptation_summary is None
    win = demo_db.get(DailyWin, first.id)
    assert win is not None
    assert win.content_schema_version == CONTENT_SCHEMA_VERSION

    result = submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    assert result.learner_state.latest_signal == "retry_after_prompt"

    child = get_demo_child(demo_db)
    assert child is not None
    context, _manifest = build_daily_win_context(demo_db, child)
    assert context.adaptation_directive is not None
    assert context.adaptation_directive.latest_signal == "retry_after_prompt"
    assert context.adaptation_directive.challenge_adjustment == "similar"
    assert any(
        "after one prompt" in event.summary
        for event in context.recent_learning_events
    )
    assert len(context.recent_daily_wins) == 1
    assert len(context.recent_learning_events) <= 10

    second = generate_demo_daily_win(demo_db, gateway)
    assert second.id != first.id
    assert second.content.adaptation_summary is not None
    assert "prompt" in second.content.adaptation_summary.lower()
    assert "tower" not in second.title.lower()
    assert second.title != first.title
    persisted = demo_db.get(DailyWin, second.id)
    assert persisted is not None
    assert persisted.content_schema_version == CONTENT_SCHEMA_VERSION
    run = demo_db.get(AiRun, persisted.ai_run_id)
    assert run is not None
    assert run.prompt_version == "daily_win_generator_v3"


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
