from daily_win_api.domains.daily_wins.enums import PersistenceSignal, SetbackResponse
from daily_win_api.domains.learning.signals import map_setback_to_signal

_OBSERVATION = {
    PersistenceSignal.INDEPENDENT_RETRY: (
        "{nickname} returned to the challenge independently."
    ),
    PersistenceSignal.RETRY_AFTER_PROMPT: (
        "{nickname} returned to the challenge after a prompt."
    ),
    PersistenceSignal.SIGNIFICANT_SUPPORT: (
        "{nickname} needed significant help after a setback."
    ),
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: (
        "{nickname} stopped or avoided after a setback."
    ),
    PersistenceSignal.NO_SIGNAL: (
        "No setback occurred during this Daily Win."
    ),
}

_NEXT = {
    PersistenceSignal.INDEPENDENT_RETRY: (
        "We'll raise the challenge slightly and wait longer before helping."
    ),
    PersistenceSignal.RETRY_AFTER_PROMPT: (
        "We'll keep the challenge similar and give {nickname} a little more "
        "time to initiate the retry."
    ),
    PersistenceSignal.SIGNIFICANT_SUPPORT: (
        "We'll simplify the first step and keep the retry small."
    ),
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: (
        "We'll shorten the challenge and make the first retry easier."
    ),
    PersistenceSignal.NO_SIGNAL: (
        "We'll keep persistence coaching as-is until a setback is observed."
    ),
}


def parent_insight(nickname: str, setback_response: str) -> dict[str, str]:
    signal = map_setback_to_signal(SetbackResponse(setback_response))
    return {
        "observation": _OBSERVATION[signal].format(nickname=nickname),
        "next_adjustment": _NEXT[signal].format(nickname=nickname),
    }
