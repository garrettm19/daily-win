"""Versioned model routing. Terra remains the baseline until evals justify a change."""

from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.domains.learning.planner import InstructionPlan

MODEL_ROUTING_V1 = "model_routing_v1"
LUNA = "gpt-5.6-luna"
TERRA = DEFAULT_OPENAI_MODEL
SOL = "gpt-5.6-sol"


def route_generator(plan: InstructionPlan | None = None) -> str:
    """Always Terra in V0.3. Future: simple plans may use Luna after eval."""
    del plan
    return TERRA


def route_evaluator(*, failed_verification: bool = False) -> str:
    if failed_verification:
        return TERRA
    return TERRA
