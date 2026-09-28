from pathlib import Path

from sqlalchemy import select

from daily_win_api.ai.delivery import (
    INTENT_BACKGROUND_PREP,
    INTENT_INTERACTIVE_WAIT,
    GenerationDelivery,
)
from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.first_win import (
    first_win_timing_snapshot,
    ready_before_guide,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.preparation import (
    PREP_READY,
    TRIGGER_FIRST_PROFILE_SETUP,
    TRIGGER_REFLECTION,
    mark_preparation_started,
    prepare_next_win,
    read_next_win_preparation,
)
from daily_win_api.domains.daily_wins.schemas import (
    AI_RUN_STATUS_FAILED,
    DailyWinGenerationError,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.observatory import build_learning_qa
from daily_win_api.eval.pricing import estimate_cost_usd
from daily_win_api.eval.terra_config import (
    EXISTING_LIVE_STEM,
    expand_blind_review_from_artifact,
)
from tests.test_v041_pregeneration import _win_count


class RecordingFake(FakeModelGateway):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.deliveries: list[GenerationDelivery] = []

    def bind_delivery(self, delivery: GenerationDelivery) -> FakeModelGateway:
        self.deliveries.append(delivery)
        return super().bind_delivery(delivery)


def test_background_preparation_uses_default_medium(demo_db) -> None:
    child = get_demo_child(demo_db)
    gateway = RecordingFake()
    prepared = prepare_next_win(
        demo_db, gateway, child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    assert prepared is not None
    assert len(gateway.deliveries) == 1
    delivery = gateway.deliveries[0]
    assert delivery.intent == INTENT_BACKGROUND_PREP
    assert delivery.reasoning_effort == "medium"
    assert delivery.requested_service_tier == "default"
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.context_manifest["generation_intent"] == INTENT_BACKGROUND_PREP
    assert run.context_manifest["reasoning_effort"] == "medium"
    assert run.context_manifest["requested_service_tier"] == "default"
    assert run.context_manifest["returned_service_tier"] == "default"


def test_interactive_wait_requests_priority(demo_db) -> None:
    child = get_demo_child(demo_db)
    gateway = RecordingFake()
    generate_demo_daily_win(demo_db, gateway, child)
    assert len(gateway.deliveries) == 1
    delivery = gateway.deliveries[0]
    assert delivery.intent == INTENT_INTERACTIVE_WAIT
    assert delivery.reasoning_effort == "medium"
    assert delivery.requested_service_tier == "fast"
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.context_manifest["requested_service_tier"] == "fast"
    assert run.context_manifest["returned_service_tier"] == "priority"
    assert run.context_manifest["reasoning_effort"] == "medium"


def test_returned_tier_recorded_separately_from_requested(demo_db) -> None:
    child = get_demo_child(demo_db)
    generate_demo_daily_win(demo_db, FakeModelGateway(), child)
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.context_manifest["requested_service_tier"] == "fast"
    assert run.context_manifest["returned_service_tier"] == "priority"
    assert run.context_manifest["service_tier"] == "priority"


def test_fallback_respects_duplicate_locking(demo_db) -> None:
    child = get_demo_child(demo_db)
    mark_preparation_started(demo_db, child, TRIGGER_FIRST_PROFILE_SETUP)
    demo_db.flush()
    gateway = RecordingFake()
    try:
        generate_demo_daily_win(demo_db, gateway, child)
        raise AssertionError("expected generation_in_progress")
    except DailyWinGenerationError as exc:
        assert exc.code == "generation_in_progress"
    assert gateway.deliveries == []
    assert gateway.calls == []
    assert _win_count(demo_db, child.id) == 0


def test_priority_failure_does_not_corrupt_state(demo_db) -> None:
    child = get_demo_child(demo_db)
    child_id = child.id
    try:
        generate_demo_daily_win(
            demo_db,
            FakeModelGateway(error=ModelGatewayError("provider_timeout")),
            child,
        )
        raise AssertionError("expected provider failure")
    except DailyWinGenerationError as exc:
        assert exc.code == "provider_timeout"
    assert get_demo_child(demo_db) is not None
    assert get_demo_child(demo_db).id == child_id
    assert _win_count(demo_db, child_id) == 0
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.status == AI_RUN_STATUS_FAILED
    assert run.context_manifest["generation_intent"] == INTENT_INTERACTIVE_WAIT
    assert run.context_manifest["requested_service_tier"] == "fast"
    wins = demo_db.scalars(
        select(DailyWin).where(DailyWin.child_id == child_id)
    ).first()
    assert wins is None


def test_learning_qa_shows_intent_and_tier(demo_db) -> None:
    child = get_demo_child(demo_db)
    generate_demo_daily_win(demo_db, FakeModelGateway(), child)
    bundle = build_learning_qa(demo_db, child)
    performance = bundle.generation_performance
    assert performance is not None
    assert performance.generation_intent == INTENT_INTERACTIVE_WAIT
    assert performance.generation_intent_label == "Interactive wait"
    assert performance.reasoning_effort == "medium"
    assert performance.requested_service_tier == "fast"
    assert performance.returned_service_tier == "priority"


def test_background_learning_qa_shows_default_tier(demo_db) -> None:
    child = get_demo_child(demo_db)
    prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    bundle = build_learning_qa(demo_db, child)
    performance = bundle.generation_performance
    assert performance is not None
    assert performance.generation_intent_label == "Background prep"
    assert performance.reasoning_effort == "medium"
    assert performance.requested_service_tier == "default"
    assert performance.returned_service_tier == "default"


def test_returning_path_never_requests_priority(demo_db) -> None:
    child = get_demo_child(demo_db)
    gateway = RecordingFake()
    prepare_next_win(demo_db, gateway, child, trigger=TRIGGER_REFLECTION)
    assert gateway.deliveries[0].requested_service_tier == "default"
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_READY
    assert status.daily_win is not None
    assert len(gateway.deliveries) == 1
    assert len(gateway.calls) == 1


def test_ready_before_guide_metric(demo_db) -> None:
    assert ready_before_guide(10_000, 20_000) is True
    assert ready_before_guide(30_000, 20_000) is False
    child = get_demo_child(demo_db)
    prepare_next_win(
        demo_db, FakeModelGateway(), child, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )
    timing = first_win_timing_snapshot(demo_db, child, onboarding_ms=30_000)
    assert timing["ready_before_guide"] is True
    unknown = first_win_timing_snapshot(demo_db, child)
    assert unknown["ready_before_guide"] is None


def test_expanded_blind_review_hides_effort_identity() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "eval-results"
        / f"{EXISTING_LIVE_STEM}.json"
    )
    review = expand_blind_review_from_artifact(source).read_text(encoding="utf-8")
    assert "### Output A" in review
    assert "### Output B" in review
    assert "### Output C" in review
    assert "Frozen InstructionPlan" in review
    assert "Required CoachProtocol" in review
    assert "Renderer contracts" in review
    assert "Preference: A / B / C / Tie" in review
    assert '"A": "low"' not in review
    assert "Output A is" not in review
    assert "Not persisted in the source metrics JSON" in review


def test_fast_mode_cost_is_double_standard() -> None:
    standard = estimate_cost_usd("gpt-5.6-terra", 2000, 1300)
    fast = estimate_cost_usd(
        "gpt-5.6-terra", 2000, 1300, service_tier="priority"
    )
    assert standard is not None and fast is not None
    assert round(fast / standard, 5) == 2.0
