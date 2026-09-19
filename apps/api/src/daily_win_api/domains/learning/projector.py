from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from daily_win_api.domains.daily_wins.enums import PersistenceSignal, TrendDirection
from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    EVENT_TYPE_SKILL_ASSESSMENT,
    AcademicEvidence,
    AcademicResult,
    project_academic_band,
)
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
from daily_win_api.domains.learning.taxonomy import is_academic_code

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


def project_academic_skill_state(
    session: Session, *, household_id, child_id, skill: Skill
) -> LearnerSkillState:
    events = session.scalars(
        select(LearningEvent)
        .where(
            LearningEvent.household_id == household_id,
            LearningEvent.child_id == child_id,
            LearningEvent.skill_id == skill.id,
            LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
            LearningEvent.supersedes_event_id.is_(None),
        )
        .order_by(LearningEvent.occurred_at.asc(), LearningEvent.created_at.asc())
    ).all()
    evidence: list[AcademicEvidence] = []
    for event in events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        raw = payload.get("result")
        if not isinstance(raw, str):
            continue
        try:
            result = AcademicResult(raw)
        except ValueError:
            continue
        session_key = str(payload.get("session_key") or event.daily_win_id or event.id)
        correct = payload.get("correct_count")
        attempted = payload.get("attempted_count")
        evidence.append(
            AcademicEvidence(
                event_id=event.id,
                occurred_at=event.occurred_at,
                result=result,
                session_key=session_key,
                correct_count=int(correct) if isinstance(correct, int) else None,
                attempted_count=int(attempted) if isinstance(attempted, int) else None,
            )
        )
    snapshot = project_academic_band(evidence, now=datetime.now(UTC))
    state_json = {
        "band": snapshot.band.value,
        "summary": snapshot.summary,
        "last_practiced_at": (
            snapshot.last_practiced_at.isoformat()
            if snapshot.last_practiced_at
            else None
        ),
        "last_independent_success_at": (
            snapshot.last_independent_success_at.isoformat()
            if snapshot.last_independent_success_at
            else None
        ),
        "usable_evidence_count": snapshot.usable_evidence_count,
        "distinct_session_count": snapshot.distinct_session_count,
        "needs_remediation": snapshot.needs_remediation,
        "reporting_kind": "measurement",
    }
    return _upsert_state(
        session,
        household_id=household_id,
        child_id=child_id,
        skill_id=skill.id,
        state_json=state_json,
        evidence_ids=snapshot.evidence_ids,
        algorithm_version=ACADEMIC_PROJECTOR_V1,
        evidence_count=snapshot.usable_evidence_count,
    )


def rebuild_child_learner_states(session: Session, *, household_id, child_id) -> None:
    project_persistence_state(session, household_id=household_id, child_id=child_id)
    skills = session.scalars(
        select(Skill).where(Skill.active.is_(True), Skill.state_mode == "mastery")
    ).all()
    measured_ids = set(
        session.scalars(
            select(LearningEvent.skill_id).where(
                LearningEvent.household_id == household_id,
                LearningEvent.child_id == child_id,
                LearningEvent.event_type == EVENT_TYPE_SKILL_ASSESSMENT,
                LearningEvent.skill_id.is_not(None),
            )
        )
    )
    for skill in skills:
        if skill.id not in measured_ids:
            continue
        if not is_academic_code(skill.code):
            continue
        project_academic_skill_state(
            session,
            household_id=household_id,
            child_id=child_id,
            skill=skill,
        )


def _upsert_state(
    session: Session,
    *,
    household_id,
    child_id,
    skill_id,
    state_json: dict[str, object],
    evidence_ids: tuple[UUID, ...],
    algorithm_version: str,
    evidence_count: int,
) -> LearnerSkillState:
    row = session.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.household_id == household_id,
            LearnerSkillState.child_id == child_id,
            LearnerSkillState.skill_id == skill_id,
        )
    )
    now = datetime.now(UTC)
    if row is None:
        row = LearnerSkillState(
            household_id=household_id,
            child_id=child_id,
            skill_id=skill_id,
            state=state_json,
            evidence_count=evidence_count,
            confidence=None,
            algorithm_version=algorithm_version,
            computed_at=now,
        )
        session.add(row)
        session.flush()
    else:
        row.state = state_json
        row.evidence_count = evidence_count
        row.confidence = None
        row.algorithm_version = algorithm_version
        row.computed_at = now
        session.flush()
        session.execute(
            delete(LearnerSkillStateEvidence).where(
                LearnerSkillStateEvidence.learner_skill_state_id == row.id
            )
        )
    for event_id in evidence_ids:
        session.add(
            LearnerSkillStateEvidence(
                learner_skill_state_id=row.id,
                learning_event_id=event_id,
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
