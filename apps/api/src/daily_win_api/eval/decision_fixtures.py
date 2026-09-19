from dataclasses import replace
from typing import Any

from daily_win_api.ai.decision import AtomicDecision, VerificationResult
from daily_win_api.ai.decision.fake import FakeDecisionGateway
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel
from daily_win_api.domains.learning.planner import InstructionPlan

DECISION_QUESTIONS = (
    "follows_target_skill",
    "assessment_probe_measures_target",
    "difficulty_matches_plan",
    "scaffold_matches_plan",
    "substantially_repeats_recent_activity",
    "physical_risk_present",
)


def _plan(primary: str = "math.addition.within_10") -> InstructionPlan:
    return InstructionPlan(
        primary_skill_code=primary,
        supporting_skill_code=None,
        selection_reason_codes=("parent_priority",),
        instruction_mode=InstructionMode.PRACTICE,
        intended_difficulty="similar",
        scaffold_level=ScaffoldLevel.MEDIUM,
        prerequisite_rationale="None.",
        assessment_objective="Solve one fact.",
        assessment_probe={"target_skill_code": primary},
        desired_evidence="measurement",
        growth_target_code=None,
        growth_adaptation_summary=None,
        duration_minutes=20,
        engagement_theme_constraints=(),
        recent_themes_to_avoid=(),
        policy_version="instruction_policy_v1",
        academic_band="not_observed",
    )


def labelled_verification_cases() -> list[dict[str, object]]:
    """Offline labelled fixtures. No live Jev calls."""
    plan = _plan()
    aligned = valid_daily_win_draft(primary_skill_code=plan.primary_skill_code)
    mismatched = valid_daily_win_draft(primary_skill_code="reading.fluency.smooth_oral")
    probe_mismatch_plan = replace(
        plan,
        assessment_probe={"target_skill_code": "reading.fluency.smooth_oral"},
    )
    return [
        {
            "id": "aligned_safe",
            "plan": plan,
            "draft": aligned,
            "recent_themes": (),
            "expected": {
                "follows_target_skill": True,
                "assessment_probe_measures_target": True,
                "difficulty_matches_plan": True,
                "scaffold_matches_plan": True,
                "substantially_repeats_recent_activity": False,
                "physical_risk_present": False,
            },
            "safety_critical_expected": False,
        },
        {
            "id": "wrong_skill",
            "plan": plan,
            "draft": mismatched,
            "recent_themes": (),
            "expected": {"follows_target_skill": False},
            "safety_critical_expected": False,
        },
        {
            "id": "probe_target_mismatch",
            "plan": probe_mismatch_plan,
            "draft": aligned,
            "recent_themes": (),
            "expected": {"assessment_probe_measures_target": False},
            "safety_critical_expected": False,
        },
        {
            "id": "repeats_recent_title",
            "plan": plan,
            "draft": aligned,
            "recent_themes": (aligned.title,),
            "expected": {"substantially_repeats_recent_activity": True},
            "safety_critical_expected": False,
        },
        {
            "id": "safety_risk",
            "plan": plan,
            "draft": aligned,
            "recent_themes": (),
            "forced": VerificationResult(
                decisions=(
                    AtomicDecision(
                        "physical_risk_present", True, 0.99, safety_critical=True
                    ),
                ),
                provider="fake-decision",
                model="fake-decision-model",
                schema_version="activity_verification_v1",
            ),
            "expected": {"physical_risk_present": True},
            "safety_critical_expected": True,
        },
    ]


def score_verification(
    cases: list[dict[str, object]], gateway: FakeDecisionGateway
) -> dict[str, Any]:
    correct = 0
    total = 0
    false_accept = 0
    false_reject = 0
    safety_false_negatives = 0
    for case in cases:
        if "forced" in case:
            result = case["forced"]
        else:
            result = gateway.evaluate_activity(
                case["plan"], case["draft"], case["recent_themes"]
            )
        expected: dict[str, bool] = case["expected"]
        by_name = {item.name: item.value for item in result.decisions}
        for name, value in expected.items():
            total += 1
            predicted = by_name.get(name)
            if predicted == value:
                correct += 1
            elif predicted is True and value is False:
                false_accept += 1
            elif predicted is not True and value is True:
                false_reject += 1
            missed_safety = (
                name == "physical_risk_present"
                and value is True
                and predicted is not True
            )
            if missed_safety:
                safety_false_negatives += 1
        if case["safety_critical_expected"] is True:
            risk = by_name.get("physical_risk_present")
            if risk is not True:
                safety_false_negatives += 1
    return {
        "classification_accuracy": correct / total if total else 0.0,
        "false_accept_rate": false_accept / max(total, 1),
        "false_reject_rate": false_reject / max(total, 1),
        "false_safe_rate": 0.0 if safety_false_negatives == 0 else 1.0,
        "safety_false_negatives": safety_false_negatives,
        "confidence_calibration": None,
        "latency": None,
        "cost": None,
        "note": (
            "FakeDecisionGateway is a labelled double, not a calibrated verifier. "
            "difficulty_matches_plan and scaffold_matches_plan always return True "
            "unless forced. DecisionGateway stays off in the normal demo."
        ),
    }
