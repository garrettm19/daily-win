from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult

ACADEMIC_PROJECTOR_V1 = "academic_projector_v1"
EVENT_TYPE_SKILL_ASSESSMENT = "skill_assessment"
SPACING_DAYS_FOR_RETAINED = 7
REVIEW_AFTER_DAYS = 14

_INDEPENDENT = AcademicResult.CORRECT_INDEPENDENTLY
_PROMPTED = AcademicResult.CORRECT_AFTER_LIGHT_PROMPT
_HELPED = AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP
_INCORRECT = AcademicResult.INCORRECT
_SKIPPED = AcademicResult.NOT_ATTEMPTED


@dataclass(frozen=True)
class AcademicEvidence:
    event_id: UUID | None
    occurred_at: datetime
    result: AcademicResult
    session_key: str
    correct_count: int | None = None
    attempted_count: int | None = None


@dataclass(frozen=True)
class AcademicStateSnapshot:
    band: AcademicBand
    algorithm_version: str
    usable_evidence_count: int
    distinct_session_count: int
    last_practiced_at: datetime | None
    last_independent_success_at: datetime | None
    evidence_ids: tuple[UUID, ...]
    summary: str
    needs_remediation: bool = False


def project_academic_band(
    evidence: list[AcademicEvidence],
    *,
    now: datetime,
) -> AcademicStateSnapshot:
    usable = [item for item in evidence if item.result != _SKIPPED]
    ids = tuple(item.event_id for item in usable if item.event_id is not None)
    if not usable:
        return AcademicStateSnapshot(
            band=AcademicBand.NOT_OBSERVED,
            algorithm_version=ACADEMIC_PROJECTOR_V1,
            usable_evidence_count=0,
            distinct_session_count=0,
            last_practiced_at=None,
            last_independent_success_at=None,
            evidence_ids=(),
            summary="No structured academic measurement yet.",
        )

    sessions = _sessions(usable)
    last_practiced = usable[-1].occurred_at
    independent_times = [
        item.occurred_at for item in usable if item.result == _INDEPENDENT
    ]
    last_independent = independent_times[-1] if independent_times else None
    independent_sessions = {
        item.session_key for item in usable if item.result == _INDEPENDENT
    }
    recent = sessions[-2:] if len(sessions) >= 2 else sessions
    recent_weak = all(_session_is_weak(group) for _key, group in recent)

    band = AcademicBand.EMERGING
    regressed = _has_regression(independent_sessions, recent_weak, sessions)
    if regressed:
        band = AcademicBand.DEVELOPING
    elif _is_retained(independent_times, now):
        band = AcademicBand.RETAINED
    elif len(independent_sessions) >= 2:
        band = AcademicBand.DEMONSTRATED
    elif any(item.result in {_INDEPENDENT, _PROMPTED} for item in usable):
        band = AcademicBand.DEVELOPING
    elif any(item.result == _HELPED for item in usable):
        band = AcademicBand.EMERGING
    else:
        band = AcademicBand.EMERGING

    return AcademicStateSnapshot(
        band=band,
        algorithm_version=ACADEMIC_PROJECTOR_V1,
        usable_evidence_count=len(usable),
        distinct_session_count=len(sessions),
        last_practiced_at=last_practiced,
        last_independent_success_at=last_independent,
        evidence_ids=ids,
        summary=_summary(band),
        needs_remediation=regressed,
    )


def due_for_review(snapshot: AcademicStateSnapshot, *, now: datetime) -> bool:
    if snapshot.band not in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}:
        return False
    practiced = snapshot.last_practiced_at
    if practiced is None:
        return True
    return now - practiced >= timedelta(days=REVIEW_AFTER_DAYS)


def _sessions(
    evidence: list[AcademicEvidence],
) -> list[tuple[str, list[AcademicEvidence]]]:
    grouped: dict[str, list[AcademicEvidence]] = {}
    order: list[str] = []
    for item in evidence:
        if item.session_key not in grouped:
            grouped[item.session_key] = []
            order.append(item.session_key)
        grouped[item.session_key].append(item)
    return [(key, grouped[key]) for key in order]


def _session_is_weak(group: list[AcademicEvidence]) -> bool:
    return all(item.result in {_INCORRECT, _HELPED, _SKIPPED} for item in group)


def _has_regression(
    independent_sessions: set[str],
    recent_weak: bool,
    sessions: list[tuple[str, list[AcademicEvidence]]],
) -> bool:
    if len(independent_sessions) < 1:
        return False
    if len(sessions) < 2:
        return False
    return recent_weak


def _is_retained(independent_times: list[datetime], now: datetime) -> bool:
    del now
    if len(independent_times) < 2:
        return False
    first = independent_times[0]
    later = [
        stamp
        for stamp in independent_times[1:]
        if stamp - first >= timedelta(days=SPACING_DAYS_FOR_RETAINED)
    ]
    return bool(later)


def _summary(band: AcademicBand) -> str:
    return {
        AcademicBand.NOT_OBSERVED: "No structured academic measurement yet.",
        AcademicBand.EMERGING: (
            "Early attempts. Independent success is not established."
        ),
        AcademicBand.DEVELOPING: "Some success, often with support. Keep practicing.",
        AcademicBand.DEMONSTRATED: (
            "Independent success in more than one session. Not yet spaced."
        ),
        AcademicBand.RETAINED: "Independent success returned after spacing.",
    }[band]
