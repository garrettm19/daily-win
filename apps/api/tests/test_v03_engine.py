from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from daily_win_api.ai.decision.fake import FakeDecisionGateway
from daily_win_api.ai.providers.fake import FakeModelGateway, valid_daily_win_draft
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.daily_wins.schemas import (
    MAX_GENERATION_ATTEMPTS,
    DailyWinFeedbackCreate,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    EvidenceKind,
)
from daily_win_api.domains.learning.models import (
    DecisionRun,
    InstructionPlanRecord,
    LearnerSkillState,
    LearningEvent,
    SkillPrerequisite,
    SkillStandardRef,
)
from daily_win_api.domains.learning.projector import rebuild_child_learner_states
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS


def test_seed_persists_curriculum_graph(demo_db) -> None:
    codes = {item["code"] for item in SKILL_DEFINITIONS}
    prereq = demo_db.scalars(select(SkillPrerequisite)).all()
    refs = demo_db.scalars(select(SkillStandardRef)).all()
    assert {row.skill_code for row in prereq} <= codes
    assert any(row.skill_code == "math.addition.within_20" for row in prereq)
    assert any(row.skill_code == "math.addition.within_10" for row in refs)
    assert not any(row.skill_code.startswith("growth.") for row in refs)


def test_generation_persists_instruction_lineage(demo_db) -> None:
    result = generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.get(DailyWin, result.id)
    assert win is not None
    assert win.instruction_plan_id is not None
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan is not None
    assert plan.reason_codes
    assert plan.plan["primary_skill_code"] == result.content.primary_skill_code
    assert "chain" not in str(plan.plan).lower()
    dumped = result.content.model_dump()
    assert "id" not in dumped
    assert "household_id" not in dumped


def test_max_retries_then_reject(demo_db) -> None:
    gateway = FakeModelGateway(
        draft=valid_daily_win_draft(primary_skill_code="invented.skill"),
        align_to_plan=False,
    )
    try:
        generate_demo_daily_win(demo_db, gateway)
        raise AssertionError("expected rejection")
    except Exception as exc:
        assert getattr(exc, "code", None) == "unknown_skill"
    assert len(gateway.calls) == MAX_GENERATION_ATTEMPTS


def test_optional_verifier_does_not_write_canonical_state(demo_db) -> None:
    before_events = demo_db.scalar(select(LearningEvent.id).limit(1))
    gateway = FakeModelGateway()
    generate_demo_daily_win(
        demo_db, gateway, decision_gateway=FakeDecisionGateway(mutate_plan=True)
    )
    runs = list(demo_db.scalars(select(DecisionRun)))
    assert runs
    assert runs[0].provider == "fake-decision"
    events = list(demo_db.scalars(select(LearningEvent)))
    if before_events is None:
        assert events == []
    child = get_demo_child(demo_db)
    assert child is not None
    states = list(
        demo_db.scalars(
            select(LearnerSkillState).where(LearnerSkillState.child_id == child.id)
        )
    )
    assert states == []


def test_academic_measurement_rebuilds_and_is_not_free_text(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db,
        generated.id,
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            setback_response=SetbackResponse.CONTINUED_AFTER_PROMPT,
            additional_note="She seemed tired and maybe gifted.",
            academic_result=AcademicResult.CORRECT_INDEPENDENTLY,
            correct_count=1,
            attempted_count=1,
        ),
    )
    child = get_demo_child(demo_db)
    assert child is not None
    measurements = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
            )
        )
    )
    assert len(measurements) == 1
    assert measurements[0].evidence_kind == EvidenceKind.MEASUREMENT.value
    assert "gifted" not in str(measurements[0].payload)
    state = demo_db.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id
            == skill_id_for_code(generated.content.primary_skill_code),
        )
    )
    assert state is not None
    assert state.algorithm_version == "academic_projector_v1"
    assert state.state["band"] == AcademicBand.DEVELOPING.value
    assert "percent" not in str(state.state)
    rebuild_child_learner_states(
        demo_db, household_id=child.household_id, child_id=child.id
    )
    again = demo_db.scalar(
        select(LearnerSkillState).where(LearnerSkillState.id == state.id)
    )
    assert again is not None
    assert again.state["band"] == state.state["band"]


def test_old_daily_win_content_schema_still_readable(demo_db) -> None:
    from daily_win_api.ai.schemas import DailyWinDraft
    from daily_win_api.domains.daily_wins.models import AiRun
    from daily_win_api.domains.daily_wins.schemas import (
        CONTENT_SCHEMA_VERSION,
        DAILY_WIN_STATUS_READY,
        INPUT_SCHEMA_VERSION,
        OPERATION_DAILY_WIN_GENERATE,
        OUTPUT_SCHEMA_VERSION,
    )

    child = get_demo_child(demo_db)
    assert child is not None
    draft = valid_daily_win_draft()
    run = AiRun(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="fake",
        model="fake-model",
        prompt_version="daily_win_generator_v3",
        input_schema_version="2",
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        status="succeeded",
        context_manifest={"legacy": True},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    demo_db.add(run)
    demo_db.flush()
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
        created_at=datetime.now(UTC) - timedelta(days=2),
    )
    demo_db.add(win)
    demo_db.flush()
    loaded = DailyWinDraft.model_validate(win.content)
    assert loaded.title == draft.title
    assert INPUT_SCHEMA_VERSION == "4"


def test_no_peer_percentile_path() -> None:
    from daily_win_api.domains.learning import academic, planner, projector

    blob = f"{academic.__file__}{planner.__file__}{projector.__file__}"
    for module in (academic, planner, projector):
        source = module.__file__
        assert source is not None
        text = open(source, encoding="utf-8").read()
        assert "percentile" not in text.lower()
        assert "norm referenced" not in text.lower()
    del blob
