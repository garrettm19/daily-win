from daily_win_api.ai.schemas import AdaptationDirective
from daily_win_api.domains.daily_wins.enums import PersistenceSignal

_POLICIES = {
    PersistenceSignal.INDEPENDENT_RETRY: (
        "slightly_increase",
        "Wait longer before helping.",
        (
            "Last time, {nickname} returned independently. Today, raise the "
            "challenge slightly and wait longer before helping."
        ),
    ),
    PersistenceSignal.RETRY_AFTER_PROMPT: (
        "similar",
        "Offer one light prompt, then give space.",
        (
            "Last time, {nickname} returned after one prompt. Today, keep the "
            "challenge similar and wait a little longer before the first prompt."
        ),
    ),
    PersistenceSignal.SIGNIFICANT_SUPPORT: (
        "reduce",
        "Offer a clearer first scaffold and keep the retry small.",
        (
            "Last time, {nickname} needed significant help. Today, simplify "
            "the first step and keep the retry small."
        ),
    ),
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: (
        "shorten",
        "Make the first retry easier and prioritize re-entry.",
        (
            "Last time, {nickname} stopped after a setback. Today, shorten "
            "the challenge and make the first retry easier."
        ),
    ),
    PersistenceSignal.NO_SIGNAL: (
        "none",
        "No persistence-specific adjustment.",
        "No persistence-specific adjustment from the last activity.",
    ),
}


def build_adaptation_directive(
    *, skill_code: str, latest_signal: str | None, nickname: str
) -> AdaptationDirective:
    try:
        signal = (
            PersistenceSignal(latest_signal)
            if latest_signal
            else PersistenceSignal.NO_SIGNAL
        )
    except ValueError:
        signal = PersistenceSignal.NO_SIGNAL
    challenge, coaching, summary = _POLICIES[signal]
    return AdaptationDirective(
        skill_code=skill_code,
        latest_signal=signal.value,
        challenge_adjustment=challenge,
        coaching_adjustment=coaching,
        parent_facing_summary=summary.format(nickname=nickname),
    )
