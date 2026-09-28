"""First-Win timing helpers. Development/demo only. No child narrative."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.schemas import AI_RUN_STATUS_SUCCEEDED

_GUIDE_DWELL: dict[str, dict[str, object]] = {}


def record_guide_dwell(
    child_id: UUID,
    *,
    dwell_ms: int,
    skipped: bool,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> None:
    """In-process Guide timing. Not analytics; not learner evidence."""
    _GUIDE_DWELL[str(child_id)] = {
        "dwell_ms": max(0, int(dwell_ms)),
        "skipped": bool(skipped),
        "started_at": started_at,
        "finished_at": finished_at,
    }


def clear_guide_dwell(child_id: UUID | None) -> None:
    if child_id is None:
        return
    _GUIDE_DWELL.pop(str(child_id), None)


def guide_dwell_for(child_id: UUID) -> dict[str, object] | None:
    stored = _GUIDE_DWELL.get(str(child_id))
    return None if stored is None else dict(stored)


def visible_wait_ms(provider_ms: int | None, onboarding_ms: int | None) -> int | None:
    """Remaining wait after useful onboarding. Never negative."""
    if provider_ms is None:
        return None
    consumed = max(0, int(onboarding_ms or 0))
    return max(0, int(provider_ms) - consumed)


def ready_before_guide(
    provider_ms: int | None, onboarding_ms: int | None
) -> bool | None:
    """True when Terra finished inside useful Guide dwell. Unknown without both."""
    if provider_ms is None or onboarding_ms is None:
        return None
    wait = visible_wait_ms(provider_ms, onboarding_ms)
    return wait == 0


def first_win_timing_snapshot(
    session: Session, child: Child, *, onboarding_ms: int | None = None
) -> dict[str, object]:
    baseline = session.scalars(
        select(ChildBaseline)
        .where(
            ChildBaseline.child_id == child.id,
            ChildBaseline.household_id == child.household_id,
        )
        .order_by(ChildBaseline.recorded_at.asc())
        .limit(1)
    ).first()
    first_run = session.scalars(
        select(AiRun)
        .where(AiRun.child_id == child.id, AiRun.household_id == child.household_id)
        .order_by(AiRun.started_at.asc())
        .limit(1)
    ).first()
    succeeded = session.scalars(
        select(AiRun)
        .where(
            AiRun.child_id == child.id,
            AiRun.household_id == child.household_id,
            AiRun.status == AI_RUN_STATUS_SUCCEEDED,
        )
        .order_by(AiRun.completed_at.asc())
        .limit(1)
    ).first()
    first_win = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
        )
        .order_by(DailyWin.created_at.asc())
        .limit(1)
    ).first()
    origin = None if baseline is None else baseline.recorded_at
    provider_ms = None
    terra_run = succeeded or first_run
    if terra_run is not None:
        provider_ms = terra_run.latency_ms
        manifest = (
            terra_run.context_manifest
            if isinstance(terra_run.context_manifest, dict)
            else {}
        )
        latency = (
            manifest.get("latency") if isinstance(manifest.get("latency"), dict) else {}
        )
        if latency.get("provider_ms") is not None:
            provider_ms = int(latency["provider_ms"])
    stored = guide_dwell_for(child.id)
    if onboarding_ms is None and stored is not None:
        raw_dwell = stored.get("dwell_ms")
        if isinstance(raw_dwell, int):
            onboarding_ms = raw_dwell
    snapshot = {
        "profile_saved_at": _iso(origin),
        "preparation_started_at": _iso(
            None if first_run is None else first_run.started_at
        ),
        "terra_completed_at": _iso(
            None if terra_run is None else terra_run.completed_at
        ),
        "win_ready_at": _iso(None if first_win is None else first_win.created_at),
        "profile_saved_ms": 0 if origin is not None else None,
        "preparation_started_ms": _offset_ms(
            origin, None if first_run is None else first_run.started_at
        ),
        "terra_completed_ms": _offset_ms(
            origin, None if terra_run is None else terra_run.completed_at
        ),
        "win_ready_ms": _offset_ms(
            origin, None if first_win is None else first_win.created_at
        ),
        "raw_model_ms": provider_ms,
        "onboarding_ms": onboarding_ms,
        "visible_wait_ms": visible_wait_ms(provider_ms, onboarding_ms),
        "ready_before_guide": ready_before_guide(provider_ms, onboarding_ms),
        "trigger": _trigger(terra_run) or _trigger(first_run),
        "guide_started_at": None if stored is None else stored.get("started_at"),
        "guide_finished_at": None if stored is None else stored.get("finished_at"),
        "guide_skipped": None if stored is None else stored.get("skipped"),
        "guide_dwell_ms": onboarding_ms,
    }
    return snapshot


def _iso(stamp: datetime | None) -> str | None:
    return None if stamp is None else stamp.isoformat()


def _offset_ms(origin: datetime | None, stamp: datetime | None) -> int | None:
    if origin is None or stamp is None:
        return None
    return max(0, int((stamp - origin).total_seconds() * 1000))


def _trigger(run: AiRun | None) -> str | None:
    if run is None or not isinstance(run.context_manifest, dict):
        return None
    value = run.context_manifest.get("generation_trigger")
    return str(value) if value else None
