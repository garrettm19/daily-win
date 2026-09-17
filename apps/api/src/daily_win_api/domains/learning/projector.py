from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from daily_win_api.domains.daily_wins.enums import PersistenceSignal, TrendDirection
from daily_win_api.domains.learning.models import (
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
    Skill,
)
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_SKILL_OBSERVATION,
    MIN_OBSERVATIONS_FOR_DIRECTION,
    PERSISTENCE_EVIDENCE_WINDOW,
    PERSISTENCE_SKILL_CODE,
    SIGNAL_RANK,
    TREND_PROJECTOR_V1,
    USABLE_PERSISTENCE_SIGNALS,
    map_setback_to_signal,
)

_SIGNAL_SUMMARY = {
    PersistenceSignal.INDEPENDENT_RETRY: (
        "Recent parent observation: returned to the challenge independently."
    ),
    PersistenceSignal.RETRY_AFTER_PROMPT: (
        "Recent parent observation: returned to the challenge after a prompt."
    ),
    PersistenceSignal.SIGNIFICANT_SUPPORT: (
        "Recent parent observation: needed significant help after a setback."
    ),
    PersistenceSignal.DISENGAGED_AFTER_SETBACK: (
        "Recent parent observation: stopped or avoided after a setback."
    ),
    PersistenceSignal.NO_SIGNAL: (
        "Recent parent observation: no setback occurred during the activity."
    ),
}


def project_persistence_state(
    session: Session, *, household_id, child_id, skill: Skill | None = None
) -> LearnerSkillState:
    """Rebuild persistence state from canonical skill_observation events."""
    resolved = skill or session.scalar(
        select(Skill).where(Skill.code == PERSISTENCE_SKILL_CODE)
    )
    if resolved is None:
        raise ValueError("missing_persistence_skill")

    events = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.household_id == household_id,
            LearningEvent.child_id == child_id,
            LearningEvent.skill_id == resolved.id,
            LearningEvent.event_type == EVENT_TYPE_SKILL_OBSERVATION,
            LearningEvent.supersedes_event_id.is_(None),
        )
        .order_by(LearningEvent.occurred_at.asc(), LearningEvent.created_at.asc())
    ).all()

    mapped: list[tuple[LearningEvent, PersistenceSignal]] = []
    for event in events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        raw_signal = payload.get("signal")
        if not isinstance(raw_signal, str):
            continue
        try:
            signal = map_setback_to_signal(raw_signal)
        except ValueError:
            try:
                signal = PersistenceSignal(raw_signal)
            except ValueError:
                continue
        mapped.append((event, signal))

    window = mapped[-PERSISTENCE_EVIDENCE_WINDOW:]
    used_events = [event for event, _signal in window]
    signals = [signal for _event, signal in window]
    latest = signals[-1] if signals else PersistenceSignal.NO_SIGNAL
    usable = [signal for signal in signals if signal in USABLE_PERSISTENCE_SIGNALS]
    direction = _direction_from_usable(usable)

    state_json = {
        "latest_signal": latest.value,
        "recent_signals": [signal.value for signal in signals],
        "summary": _SIGNAL_SUMMARY[latest],
        "direction": direction.value,
        "reporting_kind": "parent_reported",
    }

    row = session.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.household_id == household_id,
            LearnerSkillState.child_id == child_id,
            LearnerSkillState.skill_id == resolved.id,
        )
    )
    now = datetime.now(UTC)
    if row is None:
        row = LearnerSkillState(
            household_id=household_id,
            child_id=child_id,
            skill_id=resolved.id,
            state=state_json,
            evidence_count=len(used_events),
            confidence=None,
            algorithm_version=TREND_PROJECTOR_V1,
            computed_at=now,
        )
        session.add(row)
        session.flush()
    else:
        row.state = state_json
        row.evidence_count = len(used_events)
        row.confidence = None
        row.algorithm_version = TREND_PROJECTOR_V1
        row.computed_at = now
        session.flush()
        session.execute(
            delete(LearnerSkillStateEvidence).where(
                LearnerSkillStateEvidence.learner_skill_state_id == row.id
            )
        )

    for event in used_events:
        session.add(
            LearnerSkillStateEvidence(
                learner_skill_state_id=row.id,
                learning_event_id=event.id,
            )
        )
    session.flush()
    return row


def _direction_from_usable(
    usable: list[PersistenceSignal],
) -> TrendDirection:
    if len(usable) < MIN_OBSERVATIONS_FOR_DIRECTION:
        return TrendDirection.INSUFFICIENT_DATA
    ranks = [SIGNAL_RANK[signal] for signal in usable]
    midpoint = len(ranks) // 2
    earlier = sum(ranks[:midpoint]) / midpoint
    later = sum(ranks[midpoint:]) / (len(ranks) - midpoint)
    delta = later - earlier
    if delta > 0.5:
        return TrendDirection.IMPROVING
    if delta < -0.5:
        return TrendDirection.DECLINING
    return TrendDirection.STABLE
