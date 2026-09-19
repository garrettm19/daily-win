from datetime import UTC, datetime

from daily_win_api.ai.decision import AtomicDecision
from daily_win_api.ai.decision.fake import FakeDecisionGateway
from daily_win_api.ai.decision.policy import Verdict, combine_verification
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.ai.routing import MODEL_ROUTING_V1, route_evaluator, route_generator
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.domains.daily_wins.schemas import MAX_GENERATION_ATTEMPTS
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    PlannerInput,
    plan_instruction,
)
from daily_win_api.eval.decision_fixtures import (
    labelled_verification_cases,
    score_verification,
)


def _plan():
    return plan_instruction(
        PlannerInput(
            nickname="Nova",
            age_years=8,
            grade="3",
            interests=("space",),
            motivators=("stories",),
            preferred_duration_minutes=20,
            goals=(GoalPriority("math.addition", 1),),
            states={},
            recent_skill_codes=(),
            recent_themes=(),
            now=datetime(2026, 9, 19, tzinfo=UTC),
        )
    )


def test_fake_decision_gateway_labels() -> None:
    plan = _plan()
    aligned = valid_daily_win_draft(primary_skill_code=plan.primary_skill_code)
    gateway = FakeDecisionGateway()
    result = gateway.evaluate_activity(plan, aligned, ())
    assert result.schema_version == "activity_verification_v1"
    names = {item.name for item in result.decisions}
    assert "follows_target_skill" in names
    assert "physical_risk_present" in names
    assert combine_verification(result) is Verdict.PASS


def test_confidence_policy_fail_uncertain_pass() -> None:
    fail = combine_verification(
        FakeDecisionGateway(
            decisions=(
                AtomicDecision("follows_target_skill", False, 0.95),
                AtomicDecision(
                    "physical_risk_present", False, 0.95, safety_critical=True
                ),
            )
        ).evaluate_activity(_plan(), valid_daily_win_draft(), ())
    )
    uncertain = combine_verification(
        FakeDecisionGateway(
            decisions=(
                AtomicDecision("follows_target_skill", True, 0.4),
                AtomicDecision(
                    "physical_risk_present", False, 0.4, safety_critical=True
                ),
            )
        ).evaluate_activity(_plan(), valid_daily_win_draft(), ())
    )
    safety = combine_verification(
        FakeDecisionGateway(
            decisions=(
                AtomicDecision(
                    "physical_risk_present", True, 0.99, safety_critical=True
                ),
            )
        ).evaluate_activity(_plan(), valid_daily_win_draft(), ())
    )
    assert fail is Verdict.FAIL
    assert uncertain is Verdict.UNCERTAIN
    assert safety is Verdict.FAIL


def test_decision_eval_metrics_treat_safety_miss_as_severe() -> None:
    report = score_verification(labelled_verification_cases(), FakeDecisionGateway())
    assert report["false_safe_rate"] == 0
    assert "classification_accuracy" in report
    assert report["safety_false_negatives"] == 0


def test_routing_stays_on_terra() -> None:
    assert route_generator(_plan()) == DEFAULT_OPENAI_MODEL
    assert route_evaluator(failed_verification=True) == DEFAULT_OPENAI_MODEL
    assert MODEL_ROUTING_V1 == "model_routing_v1"


def test_hard_max_retries_is_three() -> None:
    assert MAX_GENERATION_ATTEMPTS == 3
