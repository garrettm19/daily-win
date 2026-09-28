"""Optional Bonus Challenges. Not academic mastery evidence."""

from __future__ import annotations

from dataclasses import dataclass

from daily_win_api.domains.learning.observations import OBSERVATION_BONUS_ENGAGEMENT
from daily_win_api.domains.learning.taxonomy import is_academic_code

BONUS_CATALOG = (
    {
        "code": "bonus.memory.sequence",
        "category": "memory",
        "title": "Remember the sequence",
        "minutes": 4,
        "prompt": "Say a short sequence of 3–5 familiar words. Can they repeat it?",
        "safety": "Sit still. No speed pressure.",
        "personal_best": True,
    },
    {
        "code": "bonus.life.organize_tomorrow",
        "category": "organization",
        "title": "Set out tomorrow's materials",
        "minutes": 5,
        "prompt": (
            "Choose two things they will need tomorrow and put them in one place."
        ),
        "safety": "Ordinary household items only.",
        "personal_best": False,
    },
    {
        "code": "bonus.communication.teach_coach",
        "category": "communication",
        "title": "Teach the coach",
        "minutes": 4,
        "prompt": (
            "Ask them to teach you the strategy they just used, in their own words."
        ),
        "safety": "No performance for an audience.",
        "personal_best": False,
    },
    {
        "code": "bonus.problem_solving.tradeoff",
        "category": "problem_solving",
        "title": "Make a tradeoff",
        "minutes": 5,
        "prompt": (
            "Offer two simple choices (time vs treat, two games). "
            "Ask them to pick and say why."
        ),
        "safety": "No money required. No real-world risk.",
        "personal_best": False,
    },
    {
        "code": "bonus.physical.balance_count",
        "category": "physical",
        "title": "Balance and count",
        "minutes": 3,
        "prompt": (
            "Stand on one foot and count to ten. Optional. "
            "Stop if wobbly or uncomfortable."
        ),
        "safety": "Indoor, shoes optional, stop for pain. Never a punishment.",
        "personal_best": True,
    },
)


@dataclass(frozen=True)
class BonusChallenge:
    code: str
    category: str
    title: str
    minutes: int
    prompt: str
    safety: str
    personal_best: bool
    optional: bool = True
    counts_as_mastery: bool = False


def choose_bonus(
    *,
    primary_skill_code: str,
    teach_the_coach: bool,
    low_engagement_categories: tuple[str, ...] = (),
    age_years: int = 8,
) -> BonusChallenge:
    del primary_skill_code
    ranked = [
        item
        for item in BONUS_CATALOG
        if item["category"] not in low_engagement_categories
    ]
    if not ranked:
        ranked = list(BONUS_CATALOG)
    if teach_the_coach:
        chosen = next(
            (
                item
                for item in ranked
                if item["code"] == "bonus.communication.teach_coach"
            ),
            ranked[0],
        )
    elif age_years < 7:
        chosen = next(
            (
                item
                for item in ranked
                if item["category"] in {"memory", "organization"}
            ),
            ranked[0],
        )
    else:
        chosen = ranked[0]
    return BonusChallenge(
        code=str(chosen["code"]),
        category=str(chosen["category"]),
        title=str(chosen["title"]),
        minutes=int(chosen["minutes"]),
        prompt=str(chosen["prompt"]),
        safety=str(chosen["safety"]),
        personal_best=bool(chosen["personal_best"]),
    )


def bonus_is_not_academic(code: str) -> bool:
    return code.startswith("bonus.") and not is_academic_code(code)


def low_engagement_categories_from_payloads(
    payloads: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    """Repeated not_into_it bonus reactions. Mechanic choice only, not mastery."""
    counts: dict[str, int] = {}
    for payload in payloads:
        if payload.get("observation_type") != OBSERVATION_BONUS_ENGAGEMENT:
            continue
        if payload.get("signal") != "not_into_it":
            continue
        category = str(payload.get("category") or "")
        if not category:
            continue
        counts[category] = counts.get(category, 0) + 1
    return tuple(category for category, count in counts.items() if count >= 2)
