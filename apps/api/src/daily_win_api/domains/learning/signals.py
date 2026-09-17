from daily_win_api.domains.daily_wins.enums import PersistenceSignal, SetbackResponse

SETBACK_TO_SIGNAL = {
    SetbackResponse.KEPT_GOING_INDEPENDENTLY: PersistenceSignal.INDEPENDENT_RETRY,
    SetbackResponse.CONTINUED_AFTER_PROMPT: PersistenceSignal.RETRY_AFTER_PROMPT,
    SetbackResponse.NEEDED_SIGNIFICANT_HELP: PersistenceSignal.SIGNIFICANT_SUPPORT,
    SetbackResponse.STOPPED_OR_AVOIDED: PersistenceSignal.DISENGAGED_AFTER_SETBACK,
    SetbackResponse.NO_SETBACK_OCCURRED: PersistenceSignal.NO_SIGNAL,
}

USABLE_PERSISTENCE_SIGNALS = frozenset(
    {
        PersistenceSignal.INDEPENDENT_RETRY,
        PersistenceSignal.RETRY_AFTER_PROMPT,
        PersistenceSignal.SIGNIFICANT_SUPPORT,
        PersistenceSignal.DISENGAGED_AFTER_SETBACK,
    }
)

EVENT_TYPE_DAILY_WIN_FEEDBACK = "daily_win_feedback"
EVENT_TYPE_SKILL_OBSERVATION = "skill_observation"
OBSERVATION_TYPE_SETBACK = "response_after_setback"
TREND_PROJECTOR_V1 = "trend_projector_v1"
PERSISTENCE_EVIDENCE_WINDOW = 5
MIN_OBSERVATIONS_FOR_DIRECTION = 3
PERSISTENCE_SKILL_CODE = "growth.persistence"

SIGNAL_RANK = {
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: 0,
    PersistenceSignal.SIGNIFICANT_SUPPORT: 1,
    PersistenceSignal.RETRY_AFTER_PROMPT: 2,
    PersistenceSignal.INDEPENDENT_RETRY: 3,
}


def map_setback_to_signal(setback_response: str) -> PersistenceSignal:
    return SETBACK_TO_SIGNAL[SetbackResponse(setback_response)]
