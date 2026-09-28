from uuid import UUID, uuid4

from sqlalchemy import func, select

from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.core.demo import get_demo_child
from daily_win_api.dev.presets import HAYES_GOAL_CODES
from daily_win_api.dev.reset import reset_demo_activity_history
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.fingerprint import compute_plan_fingerprint
from daily_win_api.domains.daily_wins.jobs import schedule_prepare_after_reflection
from daily_win_api.domains.daily_wins.latency import GenerationTimer, bind_timer, span
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.preparation import (
    PREP_FAILED,
    PREP_INVALIDATED,
    PREP_NOT_STARTED,
    PREP_READY,
    TRIGGER_FIRST_RUN,
    TRIGGER_REFLECTION,
    invalidate_unused_prepared_wins,
    prepare_next_win,
    read_next_win_preparation,
)
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_INVALIDATED,
    DailyWinGenerationError,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.models import InstructionPlanRecord
from daily_win_api.domains.learning.observatory import (
    build_learning_qa,
    build_learning_trace,
)
from tests.test_feedback_loop import CONTINUED_JSON, CONTINUED_PAYLOAD


def _win_count(session, child_id) -> int:
    return session.scalar(
        select(func.count())
        .select_from(DailyWin)
        .where(DailyWin.child_id == child_id)
    ) or 0


def test_timer_records_named_spans() -> None:
    timer = GenerationTimer()
    with bind_timer(timer):
        with span("scheduler"):
            pass
        with timer.span("provider_ms"):
            pass
    payload = timer.as_dict()
    assert payload["total_ms"] >= 0
    assert "scheduler" in payload
    assert "provider_ms" in payload


def test_generation_persists_latency_metadata(demo_db) -> None:
    result = generate_demo_daily_win(demo_db, FakeModelGateway())
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    manifest = run.context_manifest
    assert "latency" in manifest
    assert "total_ms" in manifest["latency"]
    assert "provider_ms" in manifest["latency"]
    assert manifest["generation_trigger"] == "first_run"
    assert manifest["plan_fingerprint"]
    assert result.has_feedback is False
    win = demo_db.get(DailyWin, result.id)
    assert win is not None
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan is not None
    assert plan.plan["plan_fingerprint"] == manifest["plan_fingerprint"]


def test_reflection_does_not_call_gateway(demo_db) -> None:
    win = generate_demo_daily_win(demo_db, FakeModelGateway())
    calls = {"n": 0}

    class CountingGateway(FakeModelGateway):
        def generate_daily_win(self, context):
            calls["n"] += 1
            return super().generate_daily_win(context)

    submit_demo_feedback(demo_db, win.id, CONTINUED_PAYLOAD)
    assert calls["n"] == 0


def test_prepare_after_reflection_creates_one_ready_win(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    resolved = get_demo_child(demo_db)
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), resolved, trigger=TRIGGER_REFLECTION
    )
    assert prepared is not None
    assert prepared.id != first.id
    assert prepared.has_feedback is False
    count = _win_count(demo_db, resolved.id)
    prepare_next_win(
        demo_db, FakeModelGateway(), resolved, trigger=TRIGGER_REFLECTION
    )
    assert _win_count(demo_db, resolved.id) == count


def test_manual_generate_after_prepare_does_not_duplicate(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    resolved = get_demo_child(demo_db)
    prepare_next_win(demo_db, FakeModelGateway(), resolved, trigger=TRIGGER_REFLECTION)
    try:
        generate_demo_daily_win(demo_db, FakeModelGateway())
        raise AssertionError("expected feedback_required")
    except DailyWinGenerationError as exc:
        assert exc.code == "feedback_required"
    assert _win_count(demo_db, resolved.id) == 2


def test_failed_preparation_does_not_corrupt_feedback(demo_db) -> None:
    class Boom:
        def generate_daily_win(self, context):
            raise ModelGatewayError("provider_error")

    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    resolved = get_demo_child(demo_db)
    prepared = prepare_next_win(
        demo_db, Boom(), resolved, trigger=TRIGGER_REFLECTION
    )
    assert prepared is None
    assert (
        demo_db.scalar(
            select(func.count())
            .select_from(DailyWinFeedback)
            .where(DailyWinFeedback.child_id == resolved.id)
        )
        == 1
    )
    status = read_next_win_preparation(demo_db, resolved)
    assert status.status == "failed"
    assert status.error_code == "provider_error"


def test_profile_change_invalidates_prepared_win(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    resolved = get_demo_child(demo_db)
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), resolved, trigger=TRIGGER_REFLECTION
    )
    assert prepared is not None
    changed = invalidate_unused_prepared_wins(demo_db, resolved)
    assert changed == 1
    win = demo_db.get(DailyWin, prepared.id)
    assert win is not None
    assert win.status == DAILY_WIN_STATUS_INVALIDATED
    status = read_next_win_preparation(demo_db, resolved)
    assert status.status == PREP_INVALIDATED
    assert status.daily_win is None


def test_historical_win_without_fingerprint_stays_valid(demo_db) -> None:
    result = generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.get(DailyWin, result.id)
    assert win is not None
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan is not None
    plan.plan = {
        key: value for key, value in plan.plan.items() if key != "plan_fingerprint"
    }
    demo_db.flush()
    status = read_next_win_preparation(demo_db, get_demo_child(demo_db))
    assert status.status == PREP_READY
    assert status.daily_win is not None


def test_fingerprint_changes_when_goals_change(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    first = compute_plan_fingerprint(demo_db, child)
    second = compute_plan_fingerprint(demo_db, child)
    assert first == second


def test_next_win_state_endpoint_has_no_openai(demo_db) -> None:
    from daily_win_api.api.deps import get_model_gateway
    from daily_win_api.core.config import Settings
    from daily_win_api.db.session import get_db
    from daily_win_api.main import create_app
    from tests.demo_client import DemoClient

    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_model_gateway] = lambda: FakeModelGateway()
    client = DemoClient(application)
    client.setup_hayes()
    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200
    response = client.get("/api/v1/demo/next-win-state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["preparation_status"] == "ready"
    assert payload["daily_win"] is not None
    assert payload["backend_elapsed_ms"] < 5000


def test_schedule_prepare_is_noop_when_disabled() -> None:
    called: list[object] = []
    schedule_prepare_after_reflection(uuid4(), called.append)
    assert called == []


def test_first_ever_generate_is_fallback_path(demo_db) -> None:
    result = generate_demo_daily_win(demo_db, FakeModelGateway())
    run = demo_db.get(AiRun, demo_db.get(DailyWin, result.id).ai_run_id)
    assert run is not None
    assert run.context_manifest["generation_trigger"] == TRIGGER_FIRST_RUN
    child = get_demo_child(demo_db)
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_READY
    assert status.generated_after_reflection is False


def test_rapid_reopen_reuses_one_prepared_win(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    pending = read_next_win_preparation(demo_db, child)
    assert pending.status == "generating"
    assert pending.daily_win is None
    prepare_next_win(demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION)
    ready = read_next_win_preparation(demo_db, child)
    assert ready.status == PREP_READY
    assert ready.daily_win is not None
    prepare_next_win(demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION)
    assert _win_count(demo_db, child.id) == 2


def test_manual_generate_during_visible_preparation_reuses_lock(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    generate_demo_daily_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION
    )
    try:
        generate_demo_daily_win(demo_db, FakeModelGateway(), child)
        raise AssertionError("expected feedback_required")
    except DailyWinGenerationError as exc:
        assert exc.code == "feedback_required"
    assert _win_count(demo_db, child.id) == 2


def test_bounded_retry_then_success(demo_db) -> None:
    class Flaky:
        def __init__(self) -> None:
            self.inner = FakeModelGateway()
            self.n = 0

        def generate_daily_win(self, context):
            self.n += 1
            if self.n == 1:
                raise ModelGatewayError("provider_error")
            return self.inner.generate_daily_win(context)

    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    gateway = Flaky()
    prepared = prepare_next_win(
        demo_db, gateway, child, trigger=TRIGGER_REFLECTION
    )
    assert prepared is not None
    assert gateway.n == 2
    assert read_next_win_preparation(demo_db, child).status == PREP_READY


def test_unsafe_preparation_does_not_retry(demo_db) -> None:
    class Boom:
        def __init__(self) -> None:
            self.n = 0

        def generate_daily_win(self, context):
            self.n += 1
            raise ModelGatewayError("unsafe_content")

    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    gateway = Boom()
    prepared = prepare_next_win(
        demo_db, gateway, child, trigger=TRIGGER_REFLECTION
    )
    assert prepared is None
    assert gateway.n == 1
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_FAILED
    assert status.error_code == "unsafe_content"


def test_activity_reset_returns_to_first_run_preparation(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    prepare_next_win(demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION)
    reset_demo_activity_history(
        demo_db, child_id=child.id, household_id=child.household_id
    )
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_NOT_STARTED
    assert _win_count(demo_db, child.id) == 0


def test_fingerprint_changes_when_goals_are_reordered(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    before = compute_plan_fingerprint(demo_db, child)
    from daily_win_api.core.demo import skill_id_for_code
    from daily_win_api.dev.profile import _replace_active_goals

    _replace_active_goals(
        demo_db,
        household_id=child.household_id,
        child_id=child.id,
        goal_codes=["writing.organization", "growth.persistence"],
        goal_id_for_code=lambda code: skill_id_for_code(code),
    )
    demo_db.flush()
    after = compute_plan_fingerprint(demo_db, child)
    assert after != before
    assert "writing.organization" in HAYES_GOAL_CODES


def test_learning_trace_includes_preparation_status(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    prepare_next_win(demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION)
    bundle = build_learning_qa(demo_db, child)
    assert bundle.next_win_preparation is not None
    assert bundle.next_win_preparation.status == PREP_READY
    assert bundle.next_win_preparation.generated_after_reflection is True
    assert bundle.generation_performance is not None
    assert bundle.generation_performance.latest_total_ms is not None
    trace = build_learning_trace(demo_db, child)
    assert trace.next_win_preparation is not None
    assert trace.next_win_preparation.status == PREP_READY


def test_weekly_report_does_not_create_a_win(demo_db) -> None:
    from daily_win_api.api.deps import get_model_gateway
    from daily_win_api.core.config import Settings
    from daily_win_api.db.session import get_db
    from daily_win_api.main import create_app
    from tests.demo_client import DemoClient

    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_model_gateway] = lambda: FakeModelGateway()
    client = DemoClient(application)
    client.setup_hayes()
    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200
    child_id = UUID(client.get("/api/v1/demo/child-profile").json()["child"]["id"])
    before = _win_count(demo_db, child_id)
    report = client.get("/api/v1/demo/weekly-report")
    assert report.status_code == 200
    after = _win_count(demo_db, child_id)
    assert after == before


def test_feedback_http_does_not_call_gateway(demo_db) -> None:
    from daily_win_api.api.deps import get_model_gateway
    from daily_win_api.core.config import Settings
    from daily_win_api.db.session import get_db
    from daily_win_api.main import create_app
    from tests.demo_client import DemoClient

    gateway = FakeModelGateway()
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_model_gateway] = lambda: gateway
    client = DemoClient(application)
    client.setup_hayes()
    created = client.post("/api/v1/demo/daily-wins/generate")
    assert created.status_code == 200
    calls_after_generate = len(gateway.calls)
    feedback = client.post(
        f"/api/v1/demo/daily-wins/{created.json()['id']}/feedback",
        json=CONTINUED_JSON,
    )
    assert feedback.status_code == 200, feedback.text
    assert len(gateway.calls) == calls_after_generate


def test_interest_change_invalidates_prepared_win(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_REFLECTION
    )
    assert prepared is not None
    from daily_win_api.domains.children.models import ChildBaseline

    baseline = demo_db.scalars(
        select(ChildBaseline)
        .where(ChildBaseline.child_id == child.id)
        .order_by(ChildBaseline.recorded_at.desc())
    ).first()
    assert baseline is not None
    baseline.interests = ["rock collecting"]
    demo_db.flush()
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_INVALIDATED
    win = demo_db.get(DailyWin, prepared.id)
    assert win is not None
    assert win.status == DAILY_WIN_STATUS_INVALIDATED
