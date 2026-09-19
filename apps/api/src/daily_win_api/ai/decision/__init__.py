from dataclasses import dataclass
from typing import Protocol

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.learning.planner import InstructionPlan

ACTIVITY_VERIFICATION_V1 = "activity_verification_v1"


@dataclass(frozen=True)
class AtomicDecision:
    name: str
    value: bool
    confidence: float
    safety_critical: bool = False


@dataclass(frozen=True)
class VerificationResult:
    decisions: tuple[AtomicDecision, ...]
    provider: str
    model: str
    schema_version: str


class DecisionGateway(Protocol):
    """Optional typed judgments. Never writes canonical learner truth."""

    def evaluate_activity(
        self,
        plan: InstructionPlan,
        draft: DailyWinDraft,
        recent_themes: tuple[str, ...],
    ) -> VerificationResult: ...
