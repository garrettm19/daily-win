from daily_win_api.ai.decision import (
    ACTIVITY_VERIFICATION_V1,
    AtomicDecision,
    VerificationResult,
)
from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.learning.planner import InstructionPlan


class FakeDecisionGateway:
    """Test double. Not a production provider and not Jev."""

    def __init__(
        self,
        *,
        decisions: tuple[AtomicDecision, ...] | None = None,
        mutate_plan: bool = False,
    ) -> None:
        self.decisions = decisions
        self.mutate_plan = mutate_plan
        self.calls = 0

    def evaluate_activity(
        self,
        plan: InstructionPlan,
        draft: DailyWinDraft,
        recent_themes: tuple[str, ...] = (),
    ) -> VerificationResult:
        self.calls += 1
        if self.mutate_plan:
            # Intentionally unused: callers must ignore any attempt to rewrite the plan.
            pass
        if self.decisions is not None:
            return VerificationResult(
                decisions=self.decisions,
                provider="fake-decision",
                model="fake-decision-model",
                schema_version=ACTIVITY_VERIFICATION_V1,
            )
        follows = draft.primary_skill_code == plan.primary_skill_code
        repeats = bool(recent_themes) and draft.title in recent_themes
        return VerificationResult(
            decisions=(
                AtomicDecision("follows_target_skill", follows, 0.95),
                AtomicDecision(
                    "assessment_probe_measures_target",
                    plan.assessment_probe.get("target_skill_code")
                    == plan.primary_skill_code,
                    0.9,
                ),
                AtomicDecision("difficulty_matches_plan", True, 0.8),
                AtomicDecision("scaffold_matches_plan", True, 0.8),
                AtomicDecision("substantially_repeats_recent_activity", repeats, 0.85),
                AtomicDecision(
                    "physical_risk_present", False, 0.95, safety_critical=True
                ),
                AtomicDecision("parent_instructions_are_actionable", True, 0.85),
            ),
            provider="fake-decision",
            model="fake-decision-model",
            schema_version=ACTIVITY_VERIFICATION_V1,
        )
