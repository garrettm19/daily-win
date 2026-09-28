"""Request-level generation delivery. Not educational policy.

BACKGROUND_PREP and INTERACTIVE_WAIT share scheduler, planner, CoachProtocol,
prompt v5, schema, renderer contracts, and safety. Only service tier differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

INTENT_BACKGROUND_PREP = "background_prep"
INTENT_INTERACTIVE_WAIT = "interactive_wait"

REASONING_MEDIUM = "medium"
TIER_DEFAULT = "default"
TIER_FAST = "fast"
TIER_PRIORITY = "priority"

INTENT_LABELS = {
    INTENT_BACKGROUND_PREP: "Background prep",
    INTENT_INTERACTIVE_WAIT: "Interactive wait",
}

_BACKGROUND_TRIGGERS = frozenset({"reflection", "first_profile_setup"})


@dataclass(frozen=True)
class GenerationDelivery:
    intent: str
    reasoning_effort: str
    requested_service_tier: str

    @property
    def intent_label(self) -> str:
        return INTENT_LABELS.get(self.intent, self.intent)


BACKGROUND_PREP = GenerationDelivery(
    intent=INTENT_BACKGROUND_PREP,
    reasoning_effort=REASONING_MEDIUM,
    requested_service_tier=TIER_DEFAULT,
)

INTERACTIVE_WAIT = GenerationDelivery(
    intent=INTENT_INTERACTIVE_WAIT,
    reasoning_effort=REASONING_MEDIUM,
    requested_service_tier=TIER_FAST,
)


def infer_generation_intent(*, trigger: str | None, commit_started: bool) -> str:
    """Background jobs and prep triggers stay off the interactive tier."""
    if commit_started or trigger in _BACKGROUND_TRIGGERS:
        return INTENT_BACKGROUND_PREP
    return INTENT_INTERACTIVE_WAIT


def delivery_for_intent(intent: str) -> GenerationDelivery:
    if intent == INTENT_INTERACTIVE_WAIT:
        return INTERACTIVE_WAIT
    return BACKGROUND_PREP


def bind_delivery(gateway: Any, delivery: GenerationDelivery) -> Any:
    """Apply delivery at the gateway boundary. Endpoints do not set tiers."""
    binder = getattr(gateway, "bind_delivery", None)
    if callable(binder):
        return binder(delivery)
    return gateway
