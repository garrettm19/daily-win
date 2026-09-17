import re

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError

_UNSAFE_PATTERNS = (
    r"\bscissors?\b",
    r"\bknives\b",
    r"\bknife\b",
    r"\bblades?\b",
    r"\bsharp\s+tool",
    r"\bfire\b",
    r"\bflames?\b",
    r"\bstove\b",
    r"\boven\b",
    r"\bmatches\b",
    r"\blighter\b",
    r"\bhot\s+water\b",
    r"\bboiling\b",
    r"\bchemicals?\b",
    r"\bbleach\b",
    r"\bcleaning\s+product",
    r"\bmedication\b",
    r"\bpills?\b",
    r"\btasting\b",
    r"\btaste\b",
    r"\beating\b",
    r"\beat\s+this\b",
    r"\ballergens?\b",
    r"\bchok(?:e|ing)\b",
    r"\bmarbles?\b",
    r"\bheavy\s+lift",
    r"\bclimb(?:ing)?\b",
    r"\bjump(?:ing)?\s+from\b",
    r"\bfrom\s+height\b",
    r"\bintense\s+exercise\b",
    r"\buntil\s+exhausted\b",
    r"\btraffic\b",
    r"\bcross(?:ing)?\s+the\s+street\b",
    r"\b(road|street|highway)\b",
    r"\bunsupervised\b",
    r"\bblindfold",
    r"\bheat\s+gun\b",
    r"\bsignificant\s+heat\b",
)

_UNSAFE = re.compile("|".join(_UNSAFE_PATTERNS), re.IGNORECASE)


def validate_daily_win_safety(draft: DailyWinDraft) -> None:
    """Deterministic safety check. Model safety_flags cannot override this."""
    blob = " ".join(_iter_text(draft))
    if _UNSAFE.search(blob):
        raise SafetyRejectedError


def _iter_text(draft: DailyWinDraft):
    yield draft.title
    yield draft.objective
    yield draft.personalization_summary
    yield draft.observation_focus
    yield draft.parent_briefing.purpose
    yield draft.parent_briefing.how_to_coach
    yield draft.parent_briefing.watch_for
    yield draft.parent_briefing.avoid
    yield draft.adaptations.if_too_easy
    yield draft.adaptations.if_too_hard
    yield from draft.success_checks
    yield from draft.safety_flags
    yield from (material.value for material in draft.materials)
    for segment in draft.segments:
        yield segment.title
        yield segment.parent_role
        yield from segment.steps
