import re
from collections.abc import Iterator

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError

SAFETY_VALIDATOR_VERSION = "safety_rules_v1"

# Stable rule identifiers. These may appear as development-only `dev_reason`.
SHARP_OBJECT = "sharp_object"
FIRE_OR_HEAT = "fire_or_heat"
CHEMICAL = "chemical"
MEDICATION = "medication"
EATING_OR_ALLERGEN = "eating_or_allergen"
CHOKING_HAZARD = "choking_hazard"
HEAVY_LIFTING = "heavy_lifting"
UNSAFE_CLIMBING = "unsafe_climbing"
JUMPING_FROM_HEIGHT = "jumping_from_height"
DANGEROUS_EXERCISE = "dangerous_exercise"
ROAD_OR_TRAFFIC = "road_or_traffic"
UNSUPERVISED_ACTIVITY = "unsupervised_activity"
BLINDFOLDING = "blindfolding"

SAFETY_RULE_CODES = frozenset(
    {
        SHARP_OBJECT,
        FIRE_OR_HEAT,
        CHEMICAL,
        MEDICATION,
        EATING_OR_ALLERGEN,
        CHOKING_HAZARD,
        HEAVY_LIFTING,
        UNSAFE_CLIMBING,
        JUMPING_FROM_HEIGHT,
        DANGEROUS_EXERCISE,
        ROAD_OR_TRAFFIC,
        UNSUPERVISED_ACTIVITY,
        BLINDFOLDING,
    }
)

_FLAGS = re.IGNORECASE

# Phrase-aware rules. Whole-word patterns only; a harmless substring inside
# another word must not match. Do not scan parent "avoid" / watch_for / model
# safety_flags: those fields warn against hazards and would false-positive.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        SHARP_OBJECT,
        re.compile(
            r"\b(?:scissors?|knives|knife|blades?|sharp\s+tools?)\b",
            _FLAGS,
        ),
    ),
    (
        FIRE_OR_HEAT,
        re.compile(
            r"\b(?:fires?|flames?|lighters?|candles?|"
            r"stoves?|ovens?|hot\s+water|boiling|"
            r"heat\s+gun|significant\s+heat|"
            r"light(?:ing)?\s+(?:a\s+)?candle|"
            r"use(?:s|ing)?\s+the\s+(?:stove|oven)|"
            r"matchsticks?|"
            r"(?:box|pack|book|carton)\s+of\s+match(?:es)?|"
            r"light(?:s|ing)?\s+(?:a\s+|the\s+)?match(?:es)?|"
            r"strike(?:s|ing)?\s+(?:a\s+|the\s+)?match(?:es)?|"
            r"play(?:s|ing)?\s+with\s+match(?:es)?|"
            r"use(?:s|ing)?\s+match(?:es)?)\b",
            _FLAGS,
        ),
    ),
    (
        CHEMICAL,
        re.compile(
            r"\b(?:chemicals?|bleach|cleaning\s+(?:product|products|chemicals?)|"
            r"use(?:s|ing)?\s+cleaning\s+chemicals?)\b",
            _FLAGS,
        ),
    ),
    (
        MEDICATION,
        re.compile(
            r"\b(?:medications?|pills?|take(?:s|ing)?\s+medication)\b",
            _FLAGS,
        ),
    ),
    (
        EATING_OR_ALLERGEN,
        re.compile(
            r"\b(?:tasting|taste(?:s|ing)?|eat\s+this|eating|allergens?)\b",
            _FLAGS,
        ),
    ),
    (
        CHOKING_HAZARD,
        re.compile(r"\b(?:choke|choking|marbles?)\b", _FLAGS),
    ),
    (
        HEAVY_LIFTING,
        re.compile(
            r"\b(?:heavy\s+(?:lift|lifting|object|objects|box|boxes|furniture)|"
            r"lift(?:s|ing)?\s+(?:a\s+)?heavy)\b",
            _FLAGS,
        ),
    ),
    (
        UNSAFE_CLIMBING,
        re.compile(
            r"\bclimb(?:s|ing)?\s+"
            r"(?:(?:onto|on\s+to|up(?:\s+on(?:to)?)?)\b|"
            r"(?:a|the)\s+(?:counter|counters|bookshelf|bookshelves|"
            r"furniture|chair|chairs|table|tables|roof|"
            r"cabinet|cabinets|shelf|shelves)\b)",
            _FLAGS,
        ),
    ),
    (
        JUMPING_FROM_HEIGHT,
        re.compile(
            r"\bjump(?:s|ing)?\s+(?:off|from|down\s+from)\b",
            _FLAGS,
        ),
    ),
    (
        DANGEROUS_EXERCISE,
        re.compile(
            r"\b(?:intense\s+exercise|until\s+exhausted|"
            r"dangerous\s+exercise)\b",
            _FLAGS,
        ),
    ),
    (
        ROAD_OR_TRAFFIC,
        re.compile(
            r"\b(?:cross(?:es|ing)?\s+the\s+(?:road|street|highway)|"
            r"play(?:s|ing)?\s+near\s+(?:traffic|the\s+(?:road|street))|"
            r"near\s+traffic|in\s+traffic|into\s+traffic|"
            r"in\s+the\s+(?:street|road|highway))\b",
            _FLAGS,
        ),
    ),
    (
        UNSUPERVISED_ACTIVITY,
        re.compile(
            r"\b(?:unsupervised|"
            r"without\s+(?:an?\s+)?(?:adult|parent|caregiver))\b",
            _FLAGS,
        ),
    ),
    (
        BLINDFOLDING,
        re.compile(r"\bblindfold", _FLAGS),
    ),
)


def validate_daily_win_safety(draft: DailyWinDraft) -> None:
    """Deterministic activity safety. Model safety_flags cannot override this."""
    blob = activity_text_blob(draft)
    for code, pattern in _RULES:
        if pattern.search(blob):
            raise SafetyRejectedError(code)


def activity_text_blob(draft: DailyWinDraft) -> str:
    """Concatenated activity-performing text. Excludes warning-only fields."""
    return " ".join(_activity_text(draft))


def _activity_text(draft: DailyWinDraft) -> Iterator[str]:
    """Text the child/parent is instructed to do. Excludes warning-only fields."""
    yield draft.title
    yield draft.objective
    yield draft.personalization_summary
    yield draft.observation_focus
    yield draft.parent_briefing.purpose
    yield draft.parent_briefing.how_to_coach
    yield draft.adaptations.if_too_easy
    yield draft.adaptations.if_too_hard
    yield from draft.success_checks
    yield from (material.value for material in draft.materials)
    for segment in draft.segments:
        yield segment.title
        yield segment.parent_role
        yield from segment.steps
