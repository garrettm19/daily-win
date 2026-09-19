from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from daily_win_api.ai.providers.fake import FakeModelGateway, valid_daily_win_draft
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child, skill_id_for_code
from daily_win_api.db.session import get_db
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)
from daily_win_api.domains.daily_wins.feedback import (
    FeedbackRejectedError,
    submit_demo_feedback,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.queries import get_latest_demo_daily_win
from daily_win_api.domains.daily_wins.schemas import (
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    OPERATION_DAILY_WIN_GENERATE,
    DailyWinFeedbackCreate,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    EvidenceKind,
    EvidenceSource,
)
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.models import (
    DecisionRun,
    InstructionPlanRecord,
    LearnerSkillState,
    LearningEvent,
)
from daily_win_api.domains.learning.presentation import academic_state_label
from daily_win_api.domains.learning.progress import load_demo_progress
from daily_win_api.domains.learning.projector import rebuild_child_learner_states
from daily_win_api.domains.learning.schemas import LearningEventCreate
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_SKILL_OBSERVATION,
    PERSISTENCE_SKILL_CODE,
)
from daily_win_api.main import create_app
from tests.demo_client import DemoClient
from tests.test_v02_demo import NOVA_WRITE


def _app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def _payload(result: AcademicResult | None = None) -> DailyWinFeedbackCreate:
    return DailyWinFeedbackCreate(
        difficulty=Difficulty.ABOUT_RIGHT,
        engagement=Engagement.HIGH,
        completion=Completion.COMPLETED,
        setback_response=SetbackResponse.CONTINUED_AFTER_PROMPT,
        academic_result=result,
    )


def _legacy_growth_win(session, child: Child) -> DailyWin:
    draft = valid_daily_win_draft(primary_skill_code="growth.persistence")
    run = AiRun(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="fake",
        model="fake-model",
        prompt_version="daily_win_generator_v3",
        input_schema_version="2",
        output_schema_version="2",
        status="succeeded",
        context_manifest={"legacy": True},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
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
        created_at=datetime.now(UTC),
    )
    session.add(win)
    session.flush()
    return win


def test_v4_win_exposes_parent_assessment_not_codes(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    assert child is not None
    read = get_latest_demo_daily_win(demo_db, child)
    assert read is not None
    assert read.assessment is not None
    assert "Can Hayes" in read.assessment.what_to_check
    dumped = read.model_dump()
    assert "AssessmentProbe" not in str(dumped)
    assert "success_criteria" not in str(dumped["assessment"])
    assert read.learning_engine is not None
    engine = read.learning_engine.model_dump()
    assert "id" not in engine
    assert str(child.id) not in str(engine)
    assert child.id.hex not in str(engine)
    assert "instruction_policy_v2" in engine["policy"]
    assert read.content.observation_focus
    assert "Writing" in read.learning_engine.target
    assert read.primary_skill_code == "writing.sentences.complete_sentence"


def test_academic_result_creates_separate_measurement_and_observation(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    result = submit_demo_feedback(
        demo_db,
        generated.id,
        _payload(AcademicResult.CORRECT_AFTER_LIGHT_PROMPT),
    )
    assert result.academic_observation is not None
    assert "little help" in result.academic_observation
    assert "63%" not in result.academic_observation
    assert "mastered" not in result.academic_observation.lower()
    assert result.growth_observation is not None
    assert result.what_we_learned[0].area == "Writing"
    measurements = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
            )
        )
    )
    observations = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION
            )
        )
    )
    assert len(measurements) == 1
    assert measurements[0].evidence_kind == EvidenceKind.MEASUREMENT.value
    assert measurements[0].source == EvidenceSource.PARENT.value
    assert measurements[0].payload["source"] == "parent_reported_measurement"
    assert measurements[0].payload["result"] == "correct_after_light_prompt"
    assert measurements[0].skill_id == skill_id_for_code(generated.primary_skill_code)
    assert observations[0].skill_id == skill_id_for_code(PERSISTENCE_SKILL_CODE)
    assert observations[0].evidence_kind == EvidenceKind.OBSERVATION.value
    assert observations[0].payload["signal"] == "continued_after_prompt"
    assert measurements[0].daily_win_id == observations[0].daily_win_id
    assert measurements[0].id != observations[0].id


def test_academic_result_rejected_without_probe(demo_db) -> None:
    child = get_demo_child(demo_db)
    assert child is not None
    win = _legacy_growth_win(demo_db, child)
    read = get_latest_demo_daily_win(demo_db, child)
    assert read is not None
    assert read.assessment is None
    try:
        submit_demo_feedback(
            demo_db, win.id, _payload(AcademicResult.CORRECT_INDEPENDENTLY)
        )
        raise AssertionError("expected rejection")
    except FeedbackRejectedError as exc:
        assert exc.code == "academic_result_not_applicable"


def test_legacy_win_feedback_does_not_create_academic_measurement(demo_db) -> None:
    child = get_demo_child(demo_db)
    assert child is not None
    win = _legacy_growth_win(demo_db, child)
    submit_demo_feedback(demo_db, win.id, _payload())
    measurements = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
            )
        )
    )
    observations = list(
        demo_db.scalars(
            select(LearningEvent).where(
                LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION
            )
        )
    )
    assert measurements == []
    assert observations


def test_counts_rejected_when_incomplete_and_ignored_for_qualitative(demo_db) -> None:
    try:
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            academic_result=AcademicResult.CORRECT_INDEPENDENTLY,
            correct_count=2,
        )
        raise AssertionError("expected validation error")
    except ValueError:
        pass
    try:
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            academic_result=AcademicResult.CORRECT_INDEPENDENTLY,
            correct_count=4,
            attempted_count=3,
        )
        raise AssertionError("expected validation error")
    except ValueError:
        pass
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db,
        generated.id,
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            academic_result=AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP,
            correct_count=1,
            attempted_count=1,
        ),
    )
    event = demo_db.scalar(
        select(LearningEvent).where(
            LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
        )
    )
    assert event is not None
    assert "correct_count" not in event.payload


def test_counted_probe_persists_valid_counts(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    win = demo_db.get(DailyWin, generated.id)
    assert win is not None
    plan = demo_db.get(InstructionPlanRecord, win.instruction_plan_id)
    assert plan is not None
    payload = dict(plan.plan)
    probe = dict(payload["assessment_probe"])
    probe["probe_type"] = "counted_items"
    probe["attempt_structure"] = "3-4 items"
    payload["assessment_probe"] = probe
    plan.plan = payload
    flag_modified(plan, "plan")
    demo_db.flush()
    submit_demo_feedback(
        demo_db,
        generated.id,
        DailyWinFeedbackCreate(
            difficulty=Difficulty.ABOUT_RIGHT,
            engagement=Engagement.HIGH,
            completion=Completion.COMPLETED,
            academic_result=AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
            correct_count=3,
            attempted_count=4,
        ),
    )
    event = demo_db.scalar(
        select(LearningEvent).where(
            LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT
        )
    )
    assert event is not None
    assert event.payload["correct_count"] == 3
    assert event.payload["attempted_count"] == 4


def test_extra_skill_field_is_rejected(demo_db) -> None:
    gateway = FakeModelGateway()
    client = DemoClient(_app(demo_db, gateway))
    client.setup_hayes()
    win_id = client.post("/api/v1/demo/daily-wins/generate").json()["id"]
    response = client.post(
        f"/api/v1/demo/daily-wins/{win_id}/feedback",
        json={
            "difficulty": "about_right",
            "engagement": "high",
            "completion": "completed",
            "setback_response": "continued_after_prompt",
            "academic_result": "correct_independently",
            "skill_code": "math.addition.within_10",
        },
    )
    assert response.status_code == 422


def test_http_rejects_academic_result_on_legacy_win(demo_db) -> None:
    gateway = FakeModelGateway()
    client = DemoClient(_app(demo_db, gateway))
    profile = client.setup_hayes().json()
    child = demo_db.get(Child, UUID(profile["child"]["id"]))
    assert child is not None
    win = _legacy_growth_win(demo_db, child)
    response = client.post(
        f"/api/v1/demo/daily-wins/{win.id}/feedback",
        json={
            "difficulty": "about_right",
            "engagement": "high",
            "completion": "completed",
            "setback_response": "continued_after_prompt",
            "academic_result": "correct_independently",
        },
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "academic_result_not_applicable"


def test_progress_shows_friendly_academic_state(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db, generated.id, _payload(AcademicResult.CORRECT_AFTER_LIGHT_PROMPT)
    )
    child = get_demo_child(demo_db)
    assert child is not None
    progress = load_demo_progress(demo_db, child)
    assert progress.academic_skills
    skill = progress.academic_skills[0]
    assert skill.state_label == "Developing"
    assert "little help" in (skill.recent_evidence or "").lower()
    assert skill.session_count == 1
    assert "gathering evidence" in skill.supporting_copy.lower()
    assert "%" not in str(progress.model_dump())
    assert "regressed" not in str(progress.model_dump()).lower()
    assert progress.evidence_disclaimer
    assert academic_state_label(AcademicBand.NOT_OBSERVED) == "Not enough evidence yet"
    assert academic_state_label(AcademicBand.EMERGING) == "Emerging"
    assert academic_state_label(AcademicBand.DEMONSTRATED) == "Demonstrated"
    assert academic_state_label(AcademicBand.RETAINED) == "Retained"


def test_one_success_is_not_mastery_or_retained(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    submit_demo_feedback(
        demo_db, generated.id, _payload(AcademicResult.CORRECT_INDEPENDENTLY)
    )
    child = get_demo_child(demo_db)
    assert child is not None
    state = demo_db.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id
            == skill_id_for_code(generated.primary_skill_code),
        )
    )
    assert state is not None
    assert state.state["band"] == AcademicBand.DEVELOPING.value
    assert state.state["band"] != AcademicBand.RETAINED.value
    progress = load_demo_progress(demo_db, child)
    assert progress.academic_skills[0].state_label == "Developing"


def test_verifier_remains_off_by_default(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    assert list(demo_db.scalars(select(DecisionRun))) == []


def test_nova_four_session_academic_loop(demo_db) -> None:
    gateway = FakeModelGateway()
    client = DemoClient(_app(demo_db, gateway))
    profile = client.setup_profile(NOVA_WRITE).json()
    child = demo_db.get(Child, UUID(profile["child"]["id"]))
    assert child is not None
    records: list[dict[str, object]] = []
    results = [
        AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP,
        AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
        AcademicResult.CORRECT_INDEPENDENTLY,
        AcademicResult.CORRECT_INDEPENDENTLY,
    ]
    for index, academic in enumerate(results):
        if index == 3:
            events = demo_db.scalars(
                select(LearningEvent).where(
                    LearningEvent.child_id == child.id,
                    LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
                )
            )
            past = datetime.now(UTC) - timedelta(days=8)
            for event in events:
                event.occurred_at = past
            demo_db.flush()
            rebuild_child_learner_states(
                demo_db, household_id=child.household_id, child_id=child.id
            )
        created = client.post("/api/v1/demo/daily-wins/generate")
        assert created.status_code == 200
        body = created.json()
        win_id = UUID(body["id"])
        plan_id = demo_db.scalar(
            select(DailyWin.instruction_plan_id).where(DailyWin.id == win_id)
        )
        plan = demo_db.get(InstructionPlanRecord, plan_id)
        assert plan is not None
        records.append(
            {
                "target": body["primary_skill_code"],
                "mode": plan.instruction_mode,
                "scaffold": plan.scaffold_level,
                "reasons": list(plan.reason_codes),
            }
        )
        engine = body.get("learning_engine") or {}
        assert "uuid" not in str(engine).lower()
        assert child.id.hex not in str(engine)
        assert str(child.id) not in str(engine)
        feedback = client.post(
            f"/api/v1/demo/daily-wins/{body['id']}/feedback",
            json=_payload(academic).model_dump(mode="json"),
        )
        assert feedback.status_code == 200, feedback.text
        insight = feedback.json()
        assert "mastered" not in str(insight).lower()
        assert "failed" not in str(insight).lower()
        assert insight["academic_observation"]
    state = demo_db.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id
            == skill_id_for_code("writing.sentences.complete_sentence"),
        )
    )
    assert state is not None
    assert state.state["band"] == AcademicBand.RETAINED.value
    assert records[0]["target"] == "writing.sentences.complete_sentence"
    assert records[0]["mode"] == "diagnostic"
    assert records[0]["scaffold"] == "one_prompt"
    assert records[2]["target"] == "writing.sentences.complete_sentence"
    assert records[2]["mode"] == "practice"
    assert records[2]["scaffold"] == "one_prompt"
    progress = client.get("/api/v1/demo/progress").json()
    labels = [item["state_label"] for item in progress["academic_skills"]]
    assert "Retained" in labels
    assert records[0]["reasons"]


def test_regression_uses_practice_round_copy(demo_db) -> None:
    child = get_demo_child(demo_db)
    assert child is not None
    skill_id = skill_id_for_code("writing.sentences.complete_sentence")
    now = datetime.now(UTC)
    for day, result in (
        (0, AcademicResult.CORRECT_INDEPENDENTLY),
        (1, AcademicResult.CORRECT_INDEPENDENTLY),
        (10, AcademicResult.INCORRECT),
        (11, AcademicResult.INCORRECT),
    ):
        append_learning_event(
            demo_db,
            LearningEventCreate(
                household_id=child.household_id,
                child_id=child.id,
                skill_id=skill_id,
                evidence_kind=EvidenceKind.MEASUREMENT,
                source=EvidenceSource.PARENT,
                event_type=EVENT_TYPE_SKILL_ASSESSMENT,
                occurred_at=now + timedelta(days=day - 11),
                payload={"result": result.value, "session_key": f"s{day}"},
            ),
        )
    rebuild_child_learner_states(
        demo_db, household_id=child.household_id, child_id=child.id
    )
    state = demo_db.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.child_id == child.id,
            LearnerSkillState.skill_id == skill_id,
        )
    )
    assert state is not None
    assert state.state["needs_remediation"] is True
    progress = load_demo_progress(demo_db, child)
    assert progress.academic_skills
    assert progress.academic_skills[0].state_label == "Ready for another practice round"
    assert "regressed" not in progress.academic_skills[0].state_label.lower()
    generate_demo_daily_win(demo_db, FakeModelGateway())
    plan = demo_db.scalars(
        select(InstructionPlanRecord).order_by(InstructionPlanRecord.created_at.desc())
    ).first()
    assert plan is not None
    assert plan.instruction_mode == "remediation"
    read = get_latest_demo_daily_win(demo_db, child)
    assert read is not None
    assert "regressed" not in (read.what_changed_today or "").lower()
    assert read.learning_engine is not None
    assert "Needs another practice round" in read.learning_engine.why
