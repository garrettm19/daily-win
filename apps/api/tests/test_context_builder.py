from datetime import UTC, datetime, timedelta
from uuid import uuid4

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.daily_wins.context import build_daily_win_context
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.schemas import (
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    RECENT_DAILY_WINS_CAP,
    RECENT_LEARNING_EVENTS_CAP,
)
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.schemas import LearningEventCreate


def test_context_builder_loads_current_baseline_and_goals(db_session) -> None:
    seed_development_data(db_session)
    db_session.flush()
    child = get_demo_child(db_session)
    assert child is not None

    context, manifest = build_daily_win_context(db_session, child)

    assert context.nickname == child.nickname
    assert context.parent_reported_baseline.reporting_kind == "parent_reported"
    assert context.parent_reported_baseline.age_years == 7
    assert context.parent_reported_baseline.grade == "1"
    assert context.primary_goal_skill_code == "growth.persistence"
    assert [goal.skill_code for goal in context.active_goals] == [
        "growth.persistence",
        "writing.organization",
        "growth.independence",
    ]
    assert manifest.child_id == child.id
    assert manifest.household_id == child.household_id
    assert "child_id" not in context.model_dump()
    assert "household_id" not in context.model_dump()


def test_context_builder_caps_recent_learning_events(db_session) -> None:
    seed_development_data(db_session)
    child = get_demo_child(db_session)
    assert child is not None
    base = datetime.now(UTC)
    for index in range(12):
        append_learning_event(
            db_session,
            LearningEventCreate(
                household_id=child.household_id,
                child_id=child.id,
                evidence_kind=EvidenceKind.OBSERVATION,
                source=EvidenceSource.PARENT,
                event_type=f"synthetic_event_{index}",
                occurred_at=base - timedelta(minutes=index),
                payload={"synthetic": True, "index": index},
            ),
        )
    db_session.flush()

    context, manifest = build_daily_win_context(db_session, child)

    assert len(context.recent_learning_events) == RECENT_LEARNING_EVENTS_CAP
    assert len(manifest.learning_event_ids) == RECENT_LEARNING_EVENTS_CAP
    assert context.recent_learning_events[0].event_type == "synthetic_event_0"


def test_context_builder_includes_adaptation_directive(db_session) -> None:
    seed_development_data(db_session)
    reset_demo_derived_data(db_session)
    db_session.flush()
    child = get_demo_child(db_session)
    assert child is not None

    context, _manifest = build_daily_win_context(db_session, child)

    assert context.adaptation_directive is not None
    assert context.adaptation_directive.skill_code == "growth.persistence"
    assert context.adaptation_directive.latest_signal == "no_signal"
    assert len(context.recent_learning_events) <= RECENT_LEARNING_EVENTS_CAP
    assert len(context.recent_daily_wins) <= RECENT_DAILY_WINS_CAP


def test_context_builder_caps_prior_daily_wins(db_session) -> None:
    seed_development_data(db_session)
    child = get_demo_child(db_session)
    assert child is not None
    base = datetime.now(UTC)
    for index in range(4):
        _insert_ready_daily_win(
            db_session,
            child,
            title=f"Prior Win {index}",
            created_at=base + timedelta(minutes=index),
        )
    db_session.flush()

    context, manifest = build_daily_win_context(db_session, child)

    assert len(context.recent_daily_wins) == RECENT_DAILY_WINS_CAP
    assert len(manifest.prior_daily_win_ids) == RECENT_DAILY_WINS_CAP
    assert context.recent_daily_wins[0].title == "Prior Win 3"


def _insert_ready_daily_win(
    db_session, child, title: str, created_at: datetime | None = None
) -> DailyWin:
    draft = valid_daily_win_draft(title=title)
    run = AiRun(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="fake",
        model="fake-model",
        prompt_version=PROMPT_VERSION,
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        status="succeeded",
        context_manifest={"synthetic": True},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    win = DailyWin(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        primary_skill_id=skill_id_for_code("growth.persistence"),
        ai_run_id=run.id,
        title=title,
        objective=draft.objective,
        duration_minutes=draft.duration_minutes,
        content=draft.model_dump(mode="json"),
        content_schema_version=CONTENT_SCHEMA_VERSION,
        status=DAILY_WIN_STATUS_READY,
    )
    if created_at is not None:
        win.created_at = created_at
    db_session.add(win)
    db_session.flush()
    return win
