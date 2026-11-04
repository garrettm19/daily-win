import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child
from daily_win_api.db.session import get_db
from daily_win_api.dev.presets import HAYES_GOAL_CODES, HAYES_PROFILE
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.context import prepare_daily_win_generation
from daily_win_api.domains.daily_wins.feedback import (
    FeedbackAlreadySubmittedError,
    submit_demo_feedback,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    DailyWinFeedbackCreate,
    DailyWinGenerationError,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.models import (
    ChildGoal,
    InstructionPlanRecord,
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.observatory import build_redacted_context
from daily_win_api.domains.learning.projector import rebuild_child_learner_states
from daily_win_api.eval.lineage import lineage_errors
from daily_win_api.main import create_app
from tests.demo_client import DemoClient

FEEDBACK = DailyWinFeedbackCreate(
    difficulty="about_right",
    engagement="high",
    completion="completed",
    setback_response="continued_after_prompt",
    what_helped="A reminder helped.",
    additional_note="Kept it light.",
)


def _count(session, model, child_id=None) -> int:
    stmt = select(func.count()).select_from(model)
    if child_id is not None and hasattr(model, "child_id"):
        stmt = stmt.where(model.child_id == child_id)
    return session.scalar(stmt) or 0


def _win_and_feedback(session):
    generated = generate_demo_daily_win(session, FakeModelGateway())
    child = get_demo_child(session)
    win = session.get(DailyWin, generated.id)
    submit_demo_feedback(session, win.id, FEEDBACK)
    return child, win


def test_lineage_integrity_after_reflection(demo_db) -> None:
    child, _win = _win_and_feedback(demo_db)
    assert lineage_errors(demo_db, child) == []


def test_deterministic_rebuild_matches_derived_state(demo_db) -> None:
    child, _win = _win_and_feedback(demo_db)
    before = [
        (row.skill_id, dict(row.state), row.evidence_count, row.algorithm_version)
        for row in demo_db.scalars(
            select(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
        )
    ]
    demo_db.execute(
        delete(LearnerSkillStateEvidence).where(
            LearnerSkillStateEvidence.learner_skill_state_id.in_(
                select(LearnerSkillState.id).where(
                    LearnerSkillState.child_id == child.id
                )
            )
        )
    )
    demo_db.execute(
        delete(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
    )
    demo_db.flush()
    rebuild_child_learner_states(
        demo_db, household_id=child.household_id, child_id=child.id
    )
    after = [
        (row.skill_id, dict(row.state), row.evidence_count, row.algorithm_version)
        for row in demo_db.scalars(
            select(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
        )
    ]
    assert sorted(before, key=lambda item: str(item[0])) == sorted(
        after, key=lambda item: str(item[0])
    )


def test_idempotent_feedback_and_duplicate_generation(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    win = demo_db.get(DailyWin, generated.id)
    submit_demo_feedback(demo_db, win.id, FEEDBACK)
    with pytest.raises(FeedbackAlreadySubmittedError):
        submit_demo_feedback(demo_db, win.id, FEEDBACK)
    events = _count(demo_db, LearningEvent, child.id)
    generate_demo_daily_win(demo_db, FakeModelGateway())
    with pytest.raises(DailyWinGenerationError) as exc:
        generate_demo_daily_win(demo_db, FakeModelGateway())
    assert exc.value.code == "feedback_required"
    assert _count(demo_db, LearningEvent, child.id) == events
    assert _count(demo_db, DailyWin, child.id) == 2


def test_provider_failure_does_not_persist_instruction_plan(demo_db) -> None:
    class Boom:
        def generate_daily_win(self, context):
            raise ModelGatewayError("provider_error")

    with pytest.raises(DailyWinGenerationError) as exc:
        generate_demo_daily_win(demo_db, Boom())
    assert exc.value.code == "provider_error"
    child = get_demo_child(demo_db)
    assert _count(demo_db, InstructionPlanRecord, child.id) == 0
    assert _count(demo_db, DailyWin, child.id) == 0
    runs = demo_db.scalars(select(AiRun).where(AiRun.child_id == child.id)).all()
    assert runs
    assert runs[-1].error_code == "provider_error"
    failure = runs[-1].context_manifest.get("generation_failure") or {}
    assert failure.get("api_code") == "provider_error"


def test_projector_failure_rolls_back_feedback(demo_db, monkeypatch) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    # Capture the id now: the rollback below also undoes the demo seed made in
    # this test transaction, which expires the Child instance.
    child_id = child.id
    win = demo_db.get(DailyWin, generated.id)

    def boom(*_args, **_kwargs):
        raise RuntimeError("projector")

    monkeypatch.setattr(
        "daily_win_api.domains.daily_wins.feedback.rebuild_child_learner_states",
        boom,
    )
    with pytest.raises(RuntimeError):
        submit_demo_feedback(demo_db, win.id, FEEDBACK)
    demo_db.rollback()
    assert _count(demo_db, DailyWinFeedback, child_id) == 0
    assert _count(demo_db, LearningEvent, child_id) == 0


def test_reset_clears_v03_lineage_and_keeps_profile(demo_db) -> None:
    child, _win = _win_and_feedback(demo_db)
    nickname = child.nickname
    reset_demo_derived_data(demo_db, child_id=child.id, household_id=child.household_id)
    demo_db.flush()
    assert get_demo_child(demo_db).nickname == nickname
    assert _count(demo_db, DailyWin, child.id) == 0
    assert _count(demo_db, LearningEvent, child.id) == 0
    assert _count(demo_db, LearnerSkillState, child.id) == 0
    assert _count(demo_db, InstructionPlanRecord, child.id) == 0
    assert _count(demo_db, AiRun, child.id) == 0


def test_old_historical_win_still_loads_after_later_generation(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    first = demo_db.get(DailyWin, generated.id)
    first_title = first.title
    submit_demo_feedback(demo_db, first.id, FEEDBACK)
    generate_demo_daily_win(demo_db, FakeModelGateway())
    loaded = demo_db.get(DailyWin, first.id)
    assert loaded is not None
    assert loaded.title == first_title


def test_duplicate_feedback_hits_unique_constraint(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    win = demo_db.get(DailyWin, generated.id)
    submit_demo_feedback(demo_db, win.id, FEEDBACK)
    demo_db.add(
        DailyWinFeedback(
            household_id=child.household_id,
            child_id=child.id,
            daily_win_id=win.id,
            difficulty="about_right",
            engagement="high",
            completion="completed",
            setback_response="continued_after_prompt",
            submitted_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        demo_db.flush()


def test_generation_locks_child_row() -> None:
    from daily_win_api.domains.daily_wins.service import _generate_demo_daily_win

    source = inspect.getsource(_generate_demo_daily_win)
    assert "with_for_update" in source
    assert "feedback_required" in source


def test_hot_path_indexes_exist(demo_db) -> None:
    inspector = sa_inspect(demo_db.get_bind())
    daily_win_indexes = {item["name"] for item in inspector.get_indexes("daily_wins")}
    event_indexes = {item["name"] for item in inspector.get_indexes("learning_events")}
    plan_indexes = {
        item["name"] for item in inspector.get_indexes("instruction_plans")
    }
    assert "ix_daily_wins_household_child_created" in daily_win_indexes
    assert "ix_learning_events_occurred_at" in event_indexes
    assert "ix_learning_events_child_skill_occurred" in event_indexes
    assert "ix_instruction_plans_household_child_created" in plan_indexes
    feedback_uniques = {
        item["name"] for item in inspector.get_unique_constraints("daily_win_feedback")
    }
    assert "uq_daily_win_feedback_daily_win_id" in feedback_uniques


def test_bounded_context_does_not_grow_with_250_wins(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    skill = demo_db.scalars(select(Skill).where(Skill.active.is_(True))).first()
    run = demo_db.scalars(select(AiRun).where(AiRun.child_id == child.id)).first()
    now = datetime.now(UTC)
    for index in range(250):
        win = DailyWin(
            household_id=child.household_id,
            child_id=child.id,
            primary_skill_id=skill.id,
            ai_run_id=run.id,
            title=f"Synthetic win {index}",
            objective="Bounded-context scale fixture.",
            duration_minutes=15,
            content={"title": f"Synthetic win {index}"},
            content_schema_version=CONTENT_SCHEMA_VERSION,
            status=DAILY_WIN_STATUS_READY,
        )
        demo_db.add(win)
        demo_db.flush()
        demo_db.add(
            LearningEvent(
                household_id=child.household_id,
                child_id=child.id,
                skill_id=skill.id,
                evidence_kind=EvidenceKind.OBSERVATION.value,
                source=EvidenceSource.PARENT.value,
                event_type="daily_win_feedback",
                occurred_at=now - timedelta(days=index),
                payload={"synthetic": True, "index": index},
            )
        )
    demo_db.flush()
    prep = prepare_daily_win_generation(demo_db, child)
    assert len(prep.context.bounded_evidence_summaries) <= 6
    assert len(prep.context.recent_themes) <= 3
    report = build_redacted_context(demo_db, child)
    assert report.events_included <= 10
    assert report.prior_wins_included <= 3


def _demo_app(demo_db, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def test_profile_and_goal_edits_preserve_evidence(demo_db) -> None:
    client = DemoClient(_demo_app(demo_db, FakeModelGateway()))
    client.setup_hayes()
    created = client.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200, created.text
    win_id = created.json()["id"]
    feedback = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback",
        json={
            "difficulty": "about_right",
            "engagement": "high",
            "completion": "completed",
            "setback_response": "continued_after_prompt",
        },
    )
    assert feedback.status_code == 200, feedback.text
    child_id = UUID(client.get("/api/v1/demo/child-profile").json()["child"]["id"])
    child = demo_db.get(Child, child_id)
    events_before = [
        (row.id, row.event_type, dict(row.payload))
        for row in demo_db.scalars(
            select(LearningEvent).where(LearningEvent.child_id == child.id)
        )
    ]
    states_before = [
        (row.skill_id, dict(row.state), row.evidence_count)
        for row in demo_db.scalars(
            select(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
        )
    ]
    patched = client.patch(
        "/api/v1/demo/profile",
        json={
            "interests": ["space", "animals"],
            "strengths": ["spelling"],
            "current_difficulties": ["math"],
            "response_to_difficulty": HAYES_PROFILE.response_to_difficulty,
            "goal_codes": ["math.addition", "growth.persistence"],
            "primary_goal_code": "math.addition",
            "motivators": ["choice", "short challenges"],
            "preferred_activity_minutes": 15,
        },
    )
    assert patched.status_code == 200, patched.text
    events_after = [
        (row.id, row.event_type, dict(row.payload))
        for row in demo_db.scalars(
            select(LearningEvent).where(LearningEvent.child_id == child.id)
        )
    ]
    states_after = [
        (row.skill_id, dict(row.state), row.evidence_count)
        for row in demo_db.scalars(
            select(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
        )
    ]
    assert events_after == events_before
    assert states_after == states_before
    historical = client.get(f"/api/v1/demo/daily-wins/{win_id}")
    assert historical.status_code == 200
    assert historical.json()["title"] == created.json()["title"]
    goals = list(
        demo_db.scalars(select(ChildGoal).where(ChildGoal.child_id == child.id))
    )
    assert any(not row.active for row in goals)
    assert "writing.organization" in HAYES_GOAL_CODES
    preview = client.get("/api/v1/demo/observatory/next-win-preview")
    assert preview.status_code == 200
    assert preview.json()["likely_target"].startswith("math.")
