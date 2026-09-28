from uuid import UUID, uuid4

from sqlalchemy import func, select

from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.first_win import (
    first_win_timing_snapshot,
    visible_wait_ms,
)
from daily_win_api.domains.daily_wins.jobs import (
    schedule_prepare_after_profile_setup,
    schedule_prepare_after_reflection,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.preparation import (
    PREP_FAILED,
    PREP_GENERATING,
    PREP_NOT_STARTED,
    PREP_READY,
    TRIGGER_FIRST_PROFILE_SETUP,
    mark_preparation_started,
    prepare_next_win,
    read_next_win_preparation,
)
from daily_win_api.domains.daily_wins.schemas import (
    DailyWinGenerationError,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.models import InstructionPlanRecord
from daily_win_api.domains.learning.observatory import build_learning_qa
from daily_win_api.eval.output_audit import audit_payload
from daily_win_api.eval.terra_config import run_terra_config_offline_checks
from tests.test_v041_pregeneration import _win_count


def test_visible_wait_after_onboarding() -> None:
    assert visible_wait_ms(28300, 22100) == 6200
    assert visible_wait_ms(1000, 4000) == 0
    assert visible_wait_ms(None, 1000) is None


def test_first_profile_setup_triggers_same_pipeline(demo_db) -> None:
    child = get_demo_child(demo_db)
    assert child is not None
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_NOT_STARTED
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert prepared is not None
    win = demo_db.get(DailyWin, prepared.id)
    assert win is not None
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan is not None
    assert plan.plan.get("coach_protocol")
    run = demo_db.get(AiRun, win.ai_run_id)
    assert run is not None
    assert run.prompt_version == PROMPT_VERSION
    assert run.context_manifest["generation_trigger"] == TRIGGER_FIRST_PROFILE_SETUP
    ready = read_next_win_preparation(demo_db, child)
    assert ready.status == PREP_READY
    assert ready.trigger == TRIGGER_FIRST_PROFILE_SETUP


def test_first_preparation_uses_committed_profile(demo_db) -> None:
    from daily_win_api.domains.daily_wins.fingerprint import compute_plan_fingerprint

    child = get_demo_child(demo_db)
    fingerprint = compute_plan_fingerprint(demo_db, child)
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert prepared is not None
    win = demo_db.get(DailyWin, prepared.id)
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan.plan["plan_fingerprint"] == fingerprint


def test_started_placeholder_is_generating_not_empty(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    demo_db.flush()
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_GENERATING
    assert status.trigger == TRIGGER_FIRST_PROFILE_SETUP
    assert status.focus_preview
    assert status.coach_preview


def test_skip_onboarding_while_generating_keeps_preview(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_GENERATING
    assert status.daily_win is None
    assert status.focus_preview
    assert status.coach_preview


def test_ready_before_onboarding_ends(demo_db) -> None:
    child = get_demo_child(demo_db)
    prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_READY
    timing = first_win_timing_snapshot(demo_db, child, onboarding_ms=30_000)
    assert timing["visible_wait_ms"] == 0
    assert timing["raw_model_ms"] is not None
    assert timing["ready_before_guide"] is True


def test_still_generating_after_onboarding(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    timing = first_win_timing_snapshot(demo_db, child, onboarding_ms=5_000)
    assert timing["win_ready_ms"] is None
    assert read_next_win_preparation(demo_db, child).status == PREP_GENERATING


def test_first_win_failure_keeps_profile(demo_db) -> None:
    class Boom:
        def generate_daily_win(self, context):
            raise ModelGatewayError("provider_error")

    child = get_demo_child(demo_db)
    nickname = child.nickname
    prepared = prepare_next_win(
        demo_db, Boom(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert prepared is None
    still = get_demo_child(demo_db)
    assert still is not None
    assert still.nickname == nickname
    status = read_next_win_preparation(demo_db, still)
    assert status.status == PREP_FAILED
    assert status.error_code == "provider_error"


def test_first_win_duplicate_protection(demo_db) -> None:
    child = get_demo_child(demo_db)
    first = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert first is not None
    second = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert second is not None
    assert second.id == first.id
    try:
        generate_demo_daily_win(demo_db, FakeModelGateway(), child)
        raise AssertionError("expected feedback_required")
    except DailyWinGenerationError as exc:
        assert exc.code == "feedback_required"
    assert _win_count(demo_db, child.id) == 1
    plans = demo_db.scalar(
        select(func.count())
        .select_from(InstructionPlanRecord)
        .where(InstructionPlanRecord.child_id == child.id)
    )
    assert plans == 1


def test_in_flight_generate_does_not_duplicate(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    demo_db.flush()
    try:
        generate_demo_daily_win(demo_db, FakeModelGateway(), child)
        raise AssertionError("expected generation_in_progress")
    except DailyWinGenerationError as exc:
        assert exc.code == "generation_in_progress"
    assert _win_count(demo_db, child.id) == 0


def test_profile_edit_invalidates_first_win(demo_db) -> None:
    from daily_win_api.domains.children.models import ChildBaseline
    from daily_win_api.domains.daily_wins.schemas import DAILY_WIN_STATUS_INVALIDATED

    child = get_demo_child(demo_db)
    prepared = prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert prepared is not None
    baseline = demo_db.scalars(
        select(ChildBaseline)
        .where(ChildBaseline.child_id == child.id)
        .order_by(ChildBaseline.recorded_at.desc())
    ).first()
    assert baseline is not None
    baseline.interests = ["rock collecting"]
    demo_db.flush()
    status = read_next_win_preparation(demo_db, child)
    assert status.status == "invalidated"
    win = demo_db.get(DailyWin, prepared.id)
    assert win.status == DAILY_WIN_STATUS_INVALIDATED


def test_first_win_state_in_learning_qa(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    bundle = build_learning_qa(demo_db, child)
    assert bundle.next_win_preparation is not None
    assert bundle.next_win_preparation.status == PREP_GENERATING
    assert bundle.next_win_preparation.trigger == TRIGGER_FIRST_PROFILE_SETUP
    assert bundle.first_win_timing is not None
    assert bundle.first_win_timing.trigger == TRIGGER_FIRST_PROFILE_SETUP


def test_reasoning_and_service_tier_persisted(demo_db) -> None:
    child = get_demo_child(demo_db)
    generate_demo_daily_win(
        demo_db,
        FakeModelGateway(),
        child,
        trigger=TRIGGER_FIRST_PROFILE_SETUP,
    )
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.context_manifest["reasoning_effort"] == "medium"
    assert run.context_manifest["requested_service_tier"] == "default"
    assert run.context_manifest["returned_service_tier"] == "default"
    assert run.context_manifest["service_tier"] == "default"


def test_historical_missing_fingerprint_still_valid(demo_db) -> None:
    result = generate_demo_daily_win(
        demo_db, FakeModelGateway(), trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    win = demo_db.get(DailyWin, result.id)
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    plan.plan = {
        key: value for key, value in plan.plan.items() if key != "plan_fingerprint"
    }
    demo_db.flush()
    status = read_next_win_preparation(demo_db, get_demo_child(demo_db))
    assert status.status == PREP_READY
    assert status.daily_win is not None


def test_schedule_profile_setup_is_noop_when_disabled() -> None:
    called: list[object] = []
    schedule_prepare_after_profile_setup(uuid4(), called.append)
    schedule_prepare_after_reflection(uuid4(), called.append)
    assert called == []


def test_setup_http_schedules_first_win(demo_db, monkeypatch) -> None:
    from daily_win_api.api.deps import get_model_gateway
    from daily_win_api.core.config import Settings
    from daily_win_api.db.session import get_db
    from daily_win_api.main import create_app
    from tests.demo_client import DemoClient

    scheduled: list[object] = []
    monkeypatch.setattr(
        "daily_win_api.domains.daily_wins.jobs.BACKGROUND_PREGENERATE_ENABLED",
        True,
    )
    monkeypatch.setattr(
        "daily_win_api.api.v1.demo.schedule_prepare_after_profile_setup",
        lambda child_id, add_task: scheduled.append(child_id),
    )
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_model_gateway] = lambda: FakeModelGateway()
    client = DemoClient(application)
    response = client.setup_hayes()
    assert response.status_code == 200
    assert scheduled
    from daily_win_api.domains.children.models import Child

    child = demo_db.get(Child, UUID(str(response.json()["child"]["id"])))
    assert child is not None
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_GENERATING
    assert status.trigger == TRIGGER_FIRST_PROFILE_SETUP


def test_patch_profile_does_not_schedule_generation(demo_db, monkeypatch) -> None:
    from daily_win_api.api.deps import get_model_gateway
    from daily_win_api.core.config import Settings
    from daily_win_api.db.session import get_db
    from daily_win_api.main import create_app
    from tests.demo_client import DemoClient

    scheduled: list[object] = []
    monkeypatch.setattr(
        "daily_win_api.domains.daily_wins.jobs.BACKGROUND_PREGENERATE_ENABLED",
        True,
    )
    monkeypatch.setattr(
        "daily_win_api.api.v1.demo.schedule_prepare_after_profile_setup",
        lambda child_id, add_task: scheduled.append(child_id),
    )
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_model_gateway] = lambda: FakeModelGateway()
    client = DemoClient(application)
    client.setup_hayes()
    scheduled.clear()
    profile = client.get("/api/v1/demo/child-profile").json()
    payload = {
        "interests": profile["baseline"]["interests"],
        "strengths": profile["baseline"]["strengths"],
        "current_difficulties": profile["baseline"]["current_difficulties"],
        "response_to_difficulty": profile["baseline"]["response_to_difficulty"],
        "motivators": profile["baseline"]["motivators"],
        "preferred_activity_minutes": profile["baseline"][
            "preferred_activity_minutes"
        ],
        "goal_codes": [item["skill_code"] for item in profile["goals"]],
        "primary_goal_code": profile["goals"][0]["skill_code"],
    }
    patched = client.patch("/api/v1/demo/profile", json=payload)
    assert patched.status_code == 200
    assert scheduled == []


def test_output_audit_and_terra_config_offline() -> None:
    errors = run_terra_config_offline_checks()
    assert errors == []
    audit = audit_payload()
    assert audit["do_not_cut_yet"] is True
    classes = {item["field"]: item["class"] for item in audit["fields"]}
    assert classes["title"] == "REQUIRED FOR UI"
    assert classes["success_checks"].startswith("REDUNDANT")
