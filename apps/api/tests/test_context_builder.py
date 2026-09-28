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
    BOUNDED_EVIDENCE_CAP,
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    RECENT_THEMES_CAP,
)
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.schemas import LearningEventCreate


def test_context_builder_loads_engagement_profile_and_instruction_plan(
    db_session,
) -> None:
    seed_development_data(db_session)
    db_session.flush()
    child = get_demo_child(db_session)
    assert child is not None

    context, manifest = build_daily_win_context(db_session, child)

    assert context.nickname == child.nickname
    assert context.parent_reported_baseline.reporting_kind == "parent_reported"
    assert context.parent_reported_baseline.age_years == 7
    assert context.parent_reported_baseline.grade == "1"
    assert (
        context.instruction_plan.primary_skill_code
        == "writing.organization.sequence_events"
    )
    assert "parent_priority" in context.instruction_plan.selection_reason_codes
    assert context.instruction_plan.growth_target_code == "growth.persistence"
    dumped = context.model_dump()
    assert manifest.child_id == child.id
    assert manifest.household_id == child.household_id
    assert "child_id" not in dumped
    assert "household_id" not in dumped
    assert "id" not in dumped


def test_context_builder_does_not_send_arbitrary_event_rows(db_session) -> None:
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
                payload={"synthetic": True, "index": index, "note": "secret"},
            ),
        )
    db_session.flush()

    context, _manifest = build_daily_win_context(db_session, child)
    blob = context.model_dump_json()

    assert len(context.bounded_evidence_summaries) <= BOUNDED_EVIDENCE_CAP
    assert "synthetic_event_" not in blob
    assert "secret" not in blob


def test_context_builder_includes_growth_adaptation_on_plan(db_session) -> None:
    seed_development_data(db_session)
    reset_demo_derived_data(db_session)
    db_session.flush()
    child = get_demo_child(db_session)
    assert child is not None

    context, _manifest = build_daily_win_context(db_session, child)

    assert context.instruction_plan.growth_target_code == "growth.persistence"
    assert context.instruction_plan.growth_adaptation_summary is not None
    assert len(context.recent_themes) <= RECENT_THEMES_CAP


def test_context_builder_caps_recent_themes(db_session) -> None:
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

    assert len(context.recent_themes) == RECENT_THEMES_CAP
    assert len(manifest.prior_daily_win_ids) == RECENT_THEMES_CAP
    assert context.recent_themes[0] == "Prior Win 3"
    assert "Prior Win 0" not in context.recent_themes


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
