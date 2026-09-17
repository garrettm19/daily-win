from enum import StrEnum


class Difficulty(StrEnum):
    TOO_EASY = "too_easy"
    ABOUT_RIGHT = "about_right"
    TOO_HARD = "too_hard"


class Engagement(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Completion(StrEnum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    STOPPED_EARLY = "stopped_early"


class SetbackResponse(StrEnum):
    NO_SETBACK_OCCURRED = "no_setback_occurred"
    KEPT_GOING_INDEPENDENTLY = "kept_going_independently"
    CONTINUED_AFTER_PROMPT = "continued_after_prompt"
    NEEDED_SIGNIFICANT_HELP = "needed_significant_help"
    STOPPED_OR_AVOIDED = "stopped_or_avoided"


class PersistenceSignal(StrEnum):
    INDEPENDENT_RETRY = "independent_retry"
    RETRY_AFTER_PROMPT = "retry_after_prompt"
    SIGNIFICANT_SUPPORT = "significant_support"
    DISENGAGED_AFTER_SETBACK = "disengaged_after_setback"
    NO_SIGNAL = "no_signal"


class TrendDirection(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
