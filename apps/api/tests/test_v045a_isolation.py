from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.db.session import get_db
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.models import DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import DailyWinFeedbackCreate
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import (
    AcademicResult,
    EvidenceKind,
    EvidenceSource,
)
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.models import LearningEvent
from daily_win_api.domains.learning.schemas import LearningEventCreate
from daily_win_api.domains.learning.signals import EVENT_TYPE_SKILL_OBSERVATION
from daily_win_api.main import create_app
from tests.demo_client import DemoClient
from tests.test_feedback_loop import CONTINUED_JSON, _insert_other_household_win

SESSION_A = "daily-win-test-isolation-v045a-session-a"
SESSION_B = "daily-win-test-isolation-v045a-session-b"

ACADEMIC_PAYLOAD = DailyWinFeedbackCreate(
    difficulty=Difficulty.ABOUT_RIGHT,
    engagement=Engagement.HIGH,
    completion=Completion.COMPLETED,
    setback_response=SetbackResponse.CONTINUED_AFTER_PROMPT,
    academic_result=AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
)


def _count(session, model, **filters) -> int:
    stmt = select(func.count()).select_from(model)
    for column, value in filters.items():
        stmt = stmt.where(getattr(model, column) == value)
    return session.scalar(stmt) or 0


def _development_app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _seed_unrelated_feedback_and_events(session, win) -> None:
    now = datetime.now(UTC)
    feedback = DailyWinFeedback(
        household_id=win.household_id,
        child_id=win.child_id,
        daily_win_id=win.id,
        difficulty="about_right",
        engagement="high",
        completion="completed",
        setback_response="continued_after_prompt",
        academic_result="correct_independently",
        submitted_at=now,
    )
    session.add(feedback)
    session.flush()
    append_learning_event(
        session,
        LearningEventCreate(
            household_id=win.household_id,
            child_id=win.child_id,
            skill_id=win.primary_skill_id,
            evidence_kind=EvidenceKind.MEASUREMENT,
            source=EvidenceSource.PARENT,
            event_type=EVENT_TYPE_SKILL_ASSESSMENT,
            occurred_at=now,
            payload={
                "source": "parent_reported_measurement",
                "result": "correct_independently",
            },
            daily_win_id=win.id,
            daily_win_feedback_id=feedback.id,
        ),
    )
    append_learning_event(
        session,
        LearningEventCreate(
            household_id=win.household_id,
            child_id=win.child_id,
            skill_id=skill_id_for_code("growth.persistence"),
            evidence_kind=EvidenceKind.OBSERVATION,
            source=EvidenceSource.PARENT,
            event_type=EVENT_TYPE_SKILL_OBSERVATION,
            occurred_at=now,
            payload={"signal": "continued_after_prompt"},
            daily_win_id=win.id,
            daily_win_feedback_id=feedback.id,
        ),
    )
    session.flush()


def test_background_pregenerate_is_disabled_in_pytest() -> None:
    from daily_win_api.domains.daily_wins import jobs

    assert jobs.BACKGROUND_PREGENERATE_ENABLED is False


def test_session_a_counts_never_include_session_b(demo_db) -> None:
    application = _development_app(demo_db, FakeModelGateway())
    mason = DemoClient(application, SESSION_A)
    cory = DemoClient(application, SESSION_B)
    mason.setup_hayes()
    cory.setup_hayes()

    win_a = mason.post("/api/v1/demo/daily-wins/generate")
    win_b = cory.post("/api/v1/demo/daily-wins/generate")
    assert win_a.status_code == 200
    assert win_b.status_code == 200
    assert (
        mason.post(
            f"/api/v1/demo/daily-wins/{win_a.json()['id']}/feedback",
            json=CONTINUED_JSON,
        ).status_code
        == 200
    )
    assert (
        cory.post(
            f"/api/v1/demo/daily-wins/{win_b.json()['id']}/feedback",
            json=CONTINUED_JSON,
        ).status_code
        == 200
    )

    child_a = UUID(mason.get("/api/v1/demo/child-profile").json()["child"]["id"])
    child_b = UUID(cory.get("/api/v1/demo/child-profile").json()["child"]["id"])
    assert child_a != child_b
    assert _count(demo_db, DailyWinFeedback, child_id=child_a) == 1
    assert _count(demo_db, DailyWinFeedback, child_id=child_b) == 1
    assert _count(demo_db, DailyWinFeedback, daily_win_id=UUID(win_a.json()["id"])) == 1
    assert _count(demo_db, DailyWinFeedback, daily_win_id=UUID(win_b.json()["id"])) == 1
    events_a = _count(demo_db, LearningEvent, child_id=child_a)
    events_b = _count(demo_db, LearningEvent, child_id=child_b)
    assert events_a >= 1
    assert events_b >= 1
    unscoped_feedback = _count(demo_db, DailyWinFeedback)
    unscoped_events = _count(demo_db, LearningEvent)
    assert unscoped_feedback >= 2
    assert unscoped_events >= events_a + events_b
    assert _count(demo_db, DailyWinFeedback, child_id=child_a) != unscoped_feedback
    assert _count(demo_db, LearningEvent, child_id=child_a) != unscoped_events


def test_preexisting_unrelated_rows_do_not_contaminate_assertions(demo_db) -> None:
    other = _insert_other_household_win(demo_db)
    _seed_unrelated_feedback_and_events(demo_db, other)
    child = get_demo_child(demo_db)
    assert child is not None
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(demo_db, generated.id, ACADEMIC_PAYLOAD)

    assert _count(demo_db, DailyWinFeedback, child_id=child.id) == 1
    assert _count(demo_db, DailyWinFeedback, child_id=other.child_id) == 1
    assert _count(demo_db, DailyWinFeedback, daily_win_id=generated.id) == 1

    measurements = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
                LearningEvent.daily_win_id == generated.id,
            )
        )
    )
    observations = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION,
                LearningEvent.daily_win_id == generated.id,
            )
        )
    )
    assert len(measurements) == 1
    assert measurements[0].child_id == child.id
    assert observations
    assert all(row.child_id == child.id for row in observations)

    leftover_measurements = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
            )
        )
    )
    assert len(leftover_measurements) >= 2
    leftover_feedback = _count(demo_db, DailyWinFeedback)
    assert leftover_feedback >= 2
