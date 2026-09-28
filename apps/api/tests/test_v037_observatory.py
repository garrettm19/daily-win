from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.core.config import Settings
from daily_win_api.core.demo import get_demo_child
from daily_win_api.db.session import get_db
from daily_win_api.domains.daily_wins.feedback import submit_demo_feedback
from daily_win_api.domains.daily_wins.models import DailyWin
from daily_win_api.domains.daily_wins.schemas import DailyWinFeedbackCreate
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.observatory import (
    assert_trace_is_safe,
    build_learner_snapshot,
    build_learning_trace,
    build_next_win_preview,
    build_redacted_context,
    engine_version_report,
    trace_failure_code,
)
from daily_win_api.domains.learning.planner import plan_from_dict, plan_instruction
from daily_win_api.eval.builders import planner_input
from daily_win_api.main import create_app
from tests.demo_client import DemoClient

FEEDBACK = DailyWinFeedbackCreate(
    difficulty="about_right",
    engagement="high",
    completion="completed",
    setback_response="continued_after_prompt",
)


def _app(db_session, gateway=None):
    application = create_app(Settings(app_env="development"))

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    if gateway is not None:
        application.dependency_overrides[get_model_gateway] = lambda: gateway
    return application


def test_trace_failure_code_mapping() -> None:
    assert trace_failure_code("schema_validation_failed") == "schema_error"
    assert trace_failure_code("feedback_required") == "duplicate_generation"
    assert trace_failure_code("renderer_contract_failed") == "renderer_contract_failed"


def test_engine_version_report_lists_current_policies() -> None:
    report = engine_version_report()
    assert report.curriculum_version == "curriculum_v2"
    assert report.placement_policy == "placement_policy_v1"
    assert report.instruction_policy == "instruction_policy_v4"
    assert report.instruction_scheduler == "instruction_scheduler_v1"
    assert report.academic_projector == "academic_projector_v1"
    assert report.prompt_version == "daily_win_generator_v5"
    assert report.renderer_model == "gpt-5.6-terra"
    assert_trace_is_safe(report)


def test_learning_trace_has_required_sections_without_secrets(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    assert child is not None
    trace = build_learning_trace(demo_db, child)
    assert trace.profile.nickname
    assert trace.placement.placement_policy_version == "placement_policy_v1"
    assert trace.instruction_plan.primary_skill
    assert trace.assessment.canonical_probe
    assert trace.renderer.prompt_version == "daily_win_generator_v5"
    assert trace.why_not.why_not_next_skill
    assert_trace_is_safe(trace)
    payload = trace.model_dump(mode="json")
    blob = str(payload)
    assert "sk-" not in blob
    assert "SYSTEM_PROMPT" not in blob
    assert child.id.hex not in blob.replace("-", "")


def test_placement_and_planner_and_assessment_trace_fields(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    trace = build_learning_trace(demo_db, child)
    assert trace.placement.expected_grade_band_entry_skill
    assert trace.instruction_plan.policy_version == "instruction_policy_v4"
    assert trace.assessment.probe_kind
    assert isinstance(trace.assessment.counts_apply, bool)


def test_state_before_after_and_next_preview(demo_db) -> None:
    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    win = demo_db.get(DailyWin, generated.id)
    submit_demo_feedback(demo_db, win.id, FEEDBACK)
    trace = build_learning_trace(demo_db, child, win.id)
    assert trace.reflection is not None
    assert trace.reflection.persistence_observation == "continued_after_prompt"
    assert trace.state_update
    preview = build_next_win_preview(demo_db, child)
    assert preview.likely_target
    assert "does not create" in preview.note.lower()


def test_observatory_endpoints_are_backend_authoritative(demo_db) -> None:
    client = DemoClient(_app(demo_db, FakeModelGateway()))
    client.setup_hayes()
    generated = client.post("/api/v1/demo/daily-wins/generate")
    assert generated.status_code == 200, generated.text
    versions = client.get("/api/v1/demo/observatory/engine-versions")
    assert versions.status_code == 200
    bundle = client.get("/api/v1/demo/observatory/learning-qa")
    assert bundle.status_code == 200
    body = bundle.json()
    assert body["engine"]["instruction_policy"] == "instruction_policy_v4"
    assert body["engine"]["instruction_scheduler"] == "instruction_scheduler_v1"
    trace = client.get("/api/v1/demo/observatory/learning-trace")
    assert trace.status_code == 200
    assert "profile" in trace.json()
    snapshot = client.get("/api/v1/demo/observatory/learner-snapshot")
    assert snapshot.status_code == 200
    preview = client.get("/api/v1/demo/observatory/next-win-preview")
    assert preview.status_code == 200
    context = client.get("/api/v1/demo/observatory/renderer-context")
    assert context.status_code == 200
    assert context.json()["prior_wins_included"] <= 3


def test_plan_from_dict_round_trip() -> None:
    plan = plan_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=(("writing.spelling", 1), ("growth.persistence", 2)),
        )
    )
    restored = plan_from_dict(
        {
            "primary_skill_code": plan.primary_skill_code,
            "supporting_skill_code": plan.supporting_skill_code,
            "selection_reason_codes": list(plan.selection_reason_codes),
            "instruction_mode": plan.instruction_mode.value,
            "intended_difficulty": plan.intended_difficulty,
            "scaffold_level": plan.scaffold_level.value,
            "prerequisite_rationale": plan.prerequisite_rationale,
            "assessment_objective": plan.assessment_objective,
            "assessment_probe": plan.assessment_probe,
            "desired_evidence": plan.desired_evidence,
            "growth_target_code": plan.growth_target_code,
            "growth_adaptation_summary": plan.growth_adaptation_summary,
            "duration_minutes": plan.duration_minutes,
            "engagement_theme_constraints": list(plan.engagement_theme_constraints),
            "recent_themes_to_avoid": list(plan.recent_themes_to_avoid),
            "policy_version": plan.policy_version,
            "academic_band": plan.academic_band,
            "placement_policy_version": plan.placement_policy_version,
            "placement_entry_label": plan.placement_entry_label,
            "placement_why": plan.placement_why,
            "presentation_constraint": plan.presentation_constraint,
        }
    )
    assert restored.primary_skill_code == plan.primary_skill_code
    assert restored.instruction_mode == plan.instruction_mode


def test_snapshot_and_bounded_context(demo_db) -> None:
    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    snapshot = build_learner_snapshot(demo_db, child)
    assert snapshot.nickname
    report = build_redacted_context(demo_db, child)
    assert report.events_included <= 6
    assert report.prior_wins_included <= 3
    assert_trace_is_safe(report)
