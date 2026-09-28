import re
from datetime import UTC, datetime

from sqlalchemy import func, select

from daily_win_api.ai.delivery import INTENT_INTERACTIVE_WAIT
from daily_win_api.ai.exceptions import ModelGatewayError
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.db.session import get_db
from daily_win_api.dev.presets import HAYES_GOAL_CODES
from daily_win_api.dev.profile import _replace_active_goals
from daily_win_api.dev.reset import reset_demo_activity_history
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.first_win import (
    first_win_timing_snapshot,
    record_guide_dwell,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.preparation import (
    PREP_NOT_STARTED,
    TRIGGER_FIRST_PROFILE_SETUP,
    TRIGGER_REFLECTION,
    prepare_next_win,
    read_next_win_preparation,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.coach_protocol import (
    build_coach_protocol,
    contains_generic_coach_language,
)
from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel
from daily_win_api.domains.learning.presentation import what_changed_today
from daily_win_api.domains.learning.weekly import SessionEvidence, synthesize_week
from daily_win_api.domains.learning.weekly_query import load_weekly_summary
from daily_win_api.main import create_app
from tests.demo_client import DEMO_SESSION_B, DemoClient
from tests.test_feedback_loop import CONTINUED_PAYLOAD
from tests.test_v041_pregeneration import _win_count


def _development_app(db_session, gateway=None):
    from daily_win_api.api.deps import get_model_gateway

    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def test_pilot_status_is_non_sensitive(demo_db) -> None:
    client = DemoClient(_development_app(demo_db, FakeModelGateway()))
    response = client.get("/api/v1/demo/pilot/status")
    assert response.status_code == 200
    body = response.json()
    blob = response.text.lower()
    assert "sk-" not in blob
    assert "api_key" not in blob
    assert "database_url" not in blob
    assert "postgresql" not in blob
    assert body["api"] == "ok"
    assert body["db"] == "ok"
    assert body["curriculum"] == "curriculum_v2"
    assert body["placement"] == "placement_policy_v1"
    assert body["scheduler"] == "instruction_scheduler_v1"
    assert body["instruction"] == "instruction_policy_v4"
    assert body["prompt"] == "daily_win_generator_v5"
    assert body["background_preparation"] == "available"
    assert body["generation_config"] in {"configured", "missing"}


def test_pilot_status_absent_in_production(demo_db) -> None:
    application = create_app(Settings(app_env="production"))

    def override_get_db():
        yield demo_db

    application.dependency_overrides[get_db] = override_get_db
    client = DemoClient(application)
    response = client.get("/api/v1/demo/pilot/status")
    assert response.status_code == 404


def test_ready_reopen_does_not_call_the_model(demo_db) -> None:
    gateway = FakeModelGateway()
    client = DemoClient(_development_app(demo_db, gateway))
    client.setup_hayes()
    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200
    calls = len(gateway.calls)
    response = client.get("/api/v1/demo/next-win-state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["preparation_status"] == "ready"
    assert payload["daily_win"] is not None
    assert len(gateway.calls) == calls


def test_reset_during_prepare_cannot_resurrect_win(demo_db) -> None:
    child = get_demo_child(demo_db)

    class ResettingGateway(FakeModelGateway):
        def generate_daily_win(self, context):
            reset_demo_activity_history(
                demo_db, child_id=child.id, household_id=child.household_id
            )
            demo_db.commit()
            return super().generate_daily_win(context)

    prepared = prepare_next_win(
        demo_db,
        ResettingGateway(),
        child,
        trigger=TRIGGER_FIRST_PROFILE_SETUP,
        commit_started=True,
    )
    assert prepared is None
    assert _win_count(demo_db, child.id) == 0
    status = read_next_win_preparation(demo_db, child)
    assert status.status == PREP_NOT_STARTED


def test_profile_edit_during_prepare_does_not_leave_stale_ready(demo_db) -> None:
    child = get_demo_child(demo_db)

    class EditingGateway(FakeModelGateway):
        def generate_daily_win(self, context):
            _replace_active_goals(
                demo_db,
                household_id=child.household_id,
                child_id=child.id,
                goal_codes=["writing.organization", "growth.persistence"],
                goal_id_for_code=lambda code: skill_id_for_code(code),
            )
            demo_db.flush()
            return super().generate_daily_win(context)

    prepared = prepare_next_win(
        demo_db,
        EditingGateway(),
        child,
        trigger=TRIGGER_FIRST_PROFILE_SETUP,
        commit_started=True,
    )
    assert prepared is None
    wins = demo_db.scalars(select(DailyWin).where(DailyWin.child_id == child.id))
    ready = [win for win in wins if win.status == "ready"]
    assert ready == []
    assert "writing.organization" in HAYES_GOAL_CODES


def test_background_failure_preserves_reflection(demo_db) -> None:
    first = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    child = get_demo_child(demo_db)

    class Boom(FakeModelGateway):
        def generate_daily_win(self, context):
            raise ModelGatewayError("provider_error")

    prepared = prepare_next_win(
        demo_db, Boom(), child, trigger=TRIGGER_REFLECTION
    )
    assert prepared is None
    assert (
        demo_db.scalar(
            select(func.count())
            .select_from(DailyWin)
            .where(DailyWin.child_id == child.id)
        )
        == 1
    )
    assert (
        demo_db.scalar(
            select(func.count())
            .select_from(DailyWinFeedback)
            .where(DailyWinFeedback.child_id == child.id)
        )
        == 1
    )
    status = read_next_win_preparation(demo_db, child)
    assert status.status == "failed"


def test_interactive_retry_uses_priority_request(demo_db) -> None:
    from tests.test_v042a_delivery import RecordingFake

    child = get_demo_child(demo_db)
    first = generate_demo_daily_win(demo_db, FakeModelGateway(), child)
    submit_demo_feedback(demo_db, first.id, CONTINUED_PAYLOAD)
    class Boom(FakeModelGateway):
        def generate_daily_win(self, context):
            raise ModelGatewayError("provider_error")

    prepare_next_win(demo_db, Boom(), child, trigger=TRIGGER_REFLECTION)
    gateway = RecordingFake()
    result = generate_demo_daily_win(demo_db, gateway, child)
    assert result is not None
    assert gateway.deliveries[-1].intent == INTENT_INTERACTIVE_WAIT
    assert gateway.deliveries[-1].requested_service_tier == "fast"
    run = demo_db.scalars(select(AiRun).order_by(AiRun.started_at.desc())).first()
    assert run is not None
    assert run.context_manifest["requested_service_tier"] == "fast"


def test_guide_timing_feeds_first_win_overlap(demo_db) -> None:
    child = get_demo_child(demo_db)
    generate_demo_daily_win(demo_db, FakeModelGateway(), child)
    record_guide_dwell(
        child.id,
        dwell_ms=25_000,
        skipped=False,
        started_at="2026-09-21T12:00:00+00:00",
        finished_at="2026-09-21T12:00:25+00:00",
    )
    snap = first_win_timing_snapshot(demo_db, child)
    assert snap["guide_dwell_ms"] == 25_000
    assert snap["guide_skipped"] is False
    assert snap["onboarding_ms"] == 25_000
    client = DemoClient(_development_app(demo_db, FakeModelGateway()))
    client.setup_hayes()
    posted = client.post(
        "/api/v1/demo/pilot/guide-timing",
        json={
            "guide_started_at": "2026-09-21T12:00:00Z",
            "guide_finished_at": "2026-09-21T12:00:12Z",
            "guide_skipped": True,
            "guide_dwell_ms": 12000,
        },
    )
    assert posted.status_code == 200


def test_session_restart_returns_first_run(demo_db) -> None:
    client = DemoClient(_development_app(demo_db, FakeModelGateway()))
    client.setup_hayes()
    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200
    reset = client.post("/api/v1/demo/reset/session")
    assert reset.status_code == 200
    session = client.get("/api/v1/demo/session")
    assert session.json()["status"] == "new"
    latest = client.get("/api/v1/demo/daily-wins/latest")
    assert latest.status_code in {404, 409}
    weekly = client.get("/api/v1/demo/weekly-report")
    assert weekly.status_code in {200, 409}
    if weekly.status_code == 200:
        assert weekly.json()["source_session_count"] == 0


def test_demo_sessions_stay_isolated(demo_db) -> None:
    app = _development_app(demo_db, FakeModelGateway())
    mason = DemoClient(app)
    cory = DemoClient(app, session_secret=DEMO_SESSION_B)
    mason.setup_hayes()
    mason.post("/api/v1/demo/daily-wins/generate")
    mason.post("/api/v1/demo/reset/session")
    assert cory.get("/api/v1/demo/session").json()["status"] == "new"
    cory.setup_hayes()
    assert cory.get("/api/v1/demo/session").json()["status"] == "ready"
    assert mason.get("/api/v1/demo/session").json()["status"] == "new"


def test_coach_cards_are_actionable() -> None:
    for mode in InstructionMode:
        protocol = build_coach_protocol(
            instruction_mode=mode,
            scaffold=ScaffoldLevel.MEDIUM,
            age_years=9,
            skill_code="math.addition.within_20",
            academic_band=None,
            growth_target_code="growth.persistence",
        )
        blob = " ".join(protocol.coach_card)
        assert contains_generic_coach_language(blob) is False
        assert "failed" not in blob.lower()
        assert "behind" not in blob.lower()
        assert re.search(r"\bexam\b", blob.lower()) is None
        assert "remedial" not in blob.lower()


def test_remediation_copy_is_not_punitive() -> None:
    copy = what_changed_today(
        has_prior_wins=True,
        skill_display_name="Add within 10",
        reason_codes=("regression_review",),
        instruction_mode="remediation",
        scaffold="high",
        growth_summary=None,
    )
    assert copy == "We're making this one more supported today."
    assert "failed" not in copy.lower()
    assert "behind" not in copy.lower()


def test_weekly_sparse_weeks_are_not_punitive() -> None:
    now = datetime(2026, 9, 21, 12, tzinfo=UTC)
    empty = synthesize_week((), week_start=now, week_end=now)
    one = synthesize_week(
        (
            SessionEvidence(
                skill_code="writing.organization",
                instruction_mode="practice",
                academic_result="correct_independently",
                engagement="high",
            ),
        ),
        week_start=now,
        week_end=now,
    )
    blob = " ".join(
        empty.what_looked_strong
        + empty.what_still_took_work
        + one.what_looked_strong
        + (empty.parent_coaching_suggestion, one.parent_coaching_suggestion)
    ).lower()
    assert "failed to complete" not in blob
    assert "you failed" not in blob
    assert empty.wins_completed == 0
    assert one.wins_completed == 1


def test_one_academic_goal_omits_secondary_next_week(demo_db) -> None:
    child = get_demo_child(demo_db)
    summary = load_weekly_summary(demo_db, child)
    assert summary.next_week is not None
    assert summary.next_week.secondary_academic_focus is None


def test_two_academic_goals_can_name_a_secondary(demo_db) -> None:
    child = get_demo_child(demo_db)
    _replace_active_goals(
        demo_db,
        household_id=child.household_id,
        child_id=child.id,
        goal_codes=["writing.organization", "math.addition", "growth.persistence"],
        goal_id_for_code=lambda code: skill_id_for_code(code),
    )
    demo_db.flush()
    summary = load_weekly_summary(demo_db, child)
    assert summary.next_week is not None
    assert summary.next_week.primary_academic_focus
    if summary.next_week.secondary_academic_focus:
        assert (
            summary.next_week.secondary_academic_focus
            != summary.next_week.primary_academic_focus
        )
