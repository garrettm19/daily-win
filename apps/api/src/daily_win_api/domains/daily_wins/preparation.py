"""Next-Win preparation. Educational logic stays out of FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.gateway import ModelGateway
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.feedback import feedback_exists_for_win
from daily_win_api.domains.daily_wins.fingerprint import (
    compute_plan_fingerprint,
    fingerprints_match,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.queries import to_demo_daily_win_read
from daily_win_api.domains.daily_wins.schemas import (
    AI_RUN_STATUS_FAILED,
    AI_RUN_STATUS_REJECTED,
    AI_RUN_STATUS_STARTED,
    AI_RUN_STATUS_SUCCEEDED,
    DAILY_WIN_STATUS_INVALIDATED,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    DemoDailyWinRead,
)
from daily_win_api.domains.learning.models import InstructionPlanRecord, Skill

PREP_NOT_STARTED = "not_started"
PREP_GENERATING = "generating"
PREP_READY = "ready"
PREP_FAILED = "failed"
PREP_INVALIDATED = "invalidated"

TRIGGER_REFLECTION = "reflection"
TRIGGER_MANUAL = "manual"
TRIGGER_FIRST_RUN = "first_run"
TRIGGER_FIRST_PROFILE_SETUP = "first_profile_setup"
TRIGGER_RETRY = "retry"
PREP_TRIGGERS = frozenset({TRIGGER_REFLECTION, TRIGGER_FIRST_PROFILE_SETUP})

MAX_PREGENERATION_ATTEMPTS = 2
RETRYABLE_PREP_CODES = frozenset(
    {
        "provider_error",
        "provider_timeout",
        "provider_connection_error",
        "provider_server_error",
        "rate_limited",
        "schema_validation_failed",
        "renderer_contract_failed",
        "retries_exhausted",
    }
)


@dataclass(frozen=True)
class NextWinPreparation:
    status: str
    trigger: str | None
    generation_stage: str | None
    daily_win: DemoDailyWinRead | None
    generated_after_reflection: bool
    plan_valid: bool | None
    error_code: str | None
    attempt_count: int | None
    focus_preview: str | None
    coach_preview: tuple[str, ...]
    model: str | None
    prompt_version: str | None
    latency_ms: int | None
    fingerprint_ok: bool | None


def latest_ready_win(session: Session, child: Child) -> DailyWin | None:
    return session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(1)
    ).first()


def unreflected_ready_win(session: Session, child: Child) -> DailyWin | None:
    win = latest_ready_win(session, child)
    if win is None or feedback_exists_for_win(session, win.id):
        return None
    return win


def invalidate_unused_prepared_wins(session: Session, child: Child) -> int:
    """Drop unused READY content after educationally relevant profile change."""
    win = unreflected_ready_win(session, child)
    if win is None:
        return 0
    win.status = DAILY_WIN_STATUS_INVALIDATED
    session.flush()
    return 1


def invalidate_if_fingerprint_stale(session: Session, child: Child) -> bool:
    win = unreflected_ready_win(session, child)
    if win is None:
        return False
    stored = _stored_fingerprint(session, win)
    if not stored:
        return False
    current = compute_plan_fingerprint(session, child)
    if fingerprints_match(stored, current):
        return False
    win.status = DAILY_WIN_STATUS_INVALIDATED
    session.flush()
    return True


def read_next_win_preparation(
    session: Session, child: Child
) -> NextWinPreparation:
    invalidate_if_fingerprint_stale(session, child)
    ready = unreflected_ready_win(session, child)
    if ready is not None:
        skill = session.get(Skill, ready.primary_skill_id)
        read = (
            to_demo_daily_win_read(session, ready, skill, child.nickname)
            if skill is not None
            else None
        )
        stored = _stored_fingerprint(session, ready)
        current = compute_plan_fingerprint(session, child)
        valid = fingerprints_match(stored, current)
        trigger = _trigger_for_win(session, ready)
        return NextWinPreparation(
            status=PREP_READY,
            trigger=trigger,
            generation_stage=None,
            daily_win=read,
            generated_after_reflection=trigger == TRIGGER_REFLECTION,
            plan_valid=valid,
            error_code=None,
            attempt_count=_attempt_count_for_win(session, ready),
            focus_preview=(
                None
                if read is None
                else f"{read.primary_skill_display_name}"
            ),
            coach_preview=tuple(read.coach_card) if read is not None else (),
            model=_model_for_win(session, ready),
            prompt_version=_prompt_for_win(session, ready),
            latency_ms=_latency_for_win(session, ready),
            fingerprint_ok=valid,
        )

    latest = latest_ready_win(session, child)
    last_feedback = _latest_feedback(session, child)
    latest_run = _latest_run(session, child)

    if latest_run is not None and latest_run.status == AI_RUN_STATUS_STARTED:
        preview = _focus_coach_preview(session, child)
        trigger = _trigger_from_manifest(latest_run)
        return NextWinPreparation(
            status=PREP_GENERATING,
            trigger=trigger,
            generation_stage=_stage_from_manifest(latest_run) or "building_challenge",
            daily_win=None,
            generated_after_reflection=trigger == TRIGGER_REFLECTION,
            plan_valid=None,
            error_code=None,
            attempt_count=int(
                (latest_run.context_manifest or {}).get("generation_attempt_count")
                or 1
            ),
            focus_preview=preview[0],
            coach_preview=preview[1],
            model=latest_run.model if latest_run.model != "pending" else None,
            prompt_version=latest_run.prompt_version,
            latency_ms=None,
            fingerprint_ok=None,
        )

    latest_any = _latest_win_any_status(session, child)
    if (
        latest is None
        and last_feedback is None
        and latest_any is None
        and (
            latest_run is None
            or latest_run.status
            not in {AI_RUN_STATUS_FAILED, AI_RUN_STATUS_REJECTED}
        )
    ):
        preview = _focus_coach_preview(session, child)
        return NextWinPreparation(
            status=PREP_NOT_STARTED,
            trigger=TRIGGER_FIRST_RUN,
            generation_stage="choosing_focus" if preview[0] else None,
            daily_win=None,
            generated_after_reflection=False,
            plan_valid=None,
            error_code=None,
            attempt_count=None,
            focus_preview=preview[0],
            coach_preview=preview[1],
            model=None,
            prompt_version=None,
            latency_ms=None,
            fingerprint_ok=None,
        )

    if latest_run is not None and latest_run.status in {
        AI_RUN_STATUS_FAILED,
        AI_RUN_STATUS_REJECTED,
    }:
        if last_feedback is None or latest_run.started_at >= last_feedback.submitted_at:
            return NextWinPreparation(
                status=PREP_FAILED,
                trigger=_trigger_from_manifest(latest_run),
                generation_stage=None,
                daily_win=None,
                generated_after_reflection=_trigger_from_manifest(latest_run)
                == TRIGGER_REFLECTION,
                plan_valid=None,
                error_code=latest_run.error_code,
                attempt_count=int(
                    (latest_run.context_manifest or {}).get(
                        "generation_attempt_count"
                    )
                    or 1
                ),
                focus_preview=None,
                coach_preview=(),
                model=latest_run.model if latest_run.model != "pending" else None,
                prompt_version=latest_run.prompt_version,
                latency_ms=latest_run.latency_ms,
                fingerprint_ok=None,
            )

    if (
        latest_any is not None
        and latest_any.status == DAILY_WIN_STATUS_INVALIDATED
        and (
            last_feedback is None
            or latest_any.created_at >= last_feedback.submitted_at
        )
    ):
        return NextWinPreparation(
            status=PREP_INVALIDATED,
            trigger=_trigger_for_win(session, latest_any) or TRIGGER_REFLECTION,
            generation_stage=None,
            daily_win=None,
            generated_after_reflection=_trigger_for_win(session, latest_any)
            == TRIGGER_REFLECTION,
            plan_valid=False,
            error_code="plan_fingerprint_stale",
            attempt_count=None,
            focus_preview=None,
            coach_preview=(),
            model=None,
            prompt_version=None,
            latency_ms=None,
            fingerprint_ok=False,
        )

    if last_feedback is not None:
        preview = _focus_coach_preview(session, child)
        return NextWinPreparation(
            status=PREP_GENERATING,
            trigger=TRIGGER_REFLECTION,
            generation_stage="choosing_focus",
            daily_win=None,
            generated_after_reflection=True,
            plan_valid=None,
            error_code=None,
            attempt_count=None,
            focus_preview=preview[0],
            coach_preview=preview[1],
            model=None,
            prompt_version=None,
            latency_ms=None,
            fingerprint_ok=None,
        )

    return NextWinPreparation(
        status=PREP_NOT_STARTED,
        trigger=None,
        generation_stage=None,
        daily_win=None,
        generated_after_reflection=False,
        plan_valid=None,
        error_code=None,
        attempt_count=None,
        focus_preview=None,
        coach_preview=(),
        model=None,
        prompt_version=None,
        latency_ms=None,
        fingerprint_ok=None,
    )


def mark_preparation_started(
    session: Session, child: Child, trigger: str
) -> AiRun:
    """Commit-visible STARTED row so Home can poll before Terra returns."""
    run = AiRun(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="pending",
        model="pending",
        prompt_version=PROMPT_VERSION,
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        status=AI_RUN_STATUS_STARTED,
        context_manifest={
            "generation_trigger": trigger,
            "generation_stage": "building_challenge",
        },
        started_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    return run


def prepare_next_win(
    session: Session,
    gateway: ModelGateway,
    child: Child,
    *,
    trigger: str = TRIGGER_REFLECTION,
    commit_started: bool = False,
) -> DemoDailyWinRead | None:
    from daily_win_api.domains.daily_wins.schemas import DailyWinGenerationError
    from daily_win_api.domains.daily_wins.service import generate_demo_daily_win

    for attempt in range(MAX_PREGENERATION_ATTEMPTS):
        try:
            return generate_demo_daily_win(
                session,
                gateway,
                child,
                trigger=trigger,
                max_attempts=MAX_PREGENERATION_ATTEMPTS,
                commit_started=commit_started,
            )
        except DailyWinGenerationError as exc:
            if exc.code == "feedback_required":
                ready = unreflected_ready_win(session, child)
                if ready is None:
                    return None
                skill = session.get(Skill, ready.primary_skill_id)
                if skill is None:
                    return None
                return to_demo_daily_win_read(session, ready, skill, child.nickname)
            if exc.code in {"generation_in_progress", "superseded"}:
                return None
            if (
                attempt + 1 >= MAX_PREGENERATION_ATTEMPTS
                or exc.code not in RETRYABLE_PREP_CODES
            ):
                return None
    return None


def generation_performance_snapshot(
    session: Session, child: Child
) -> dict[str, object]:
    from daily_win_api.ai.delivery import INTENT_LABELS

    runs = session.scalars(
        select(AiRun)
        .where(
            AiRun.child_id == child.id,
            AiRun.household_id == child.household_id,
            AiRun.status == AI_RUN_STATUS_SUCCEEDED,
        )
        .order_by(AiRun.completed_at.desc())
        .limit(5)
    ).all()
    latest = runs[0] if runs else None
    totals = [int(run.latency_ms) for run in runs if run.latency_ms is not None]
    providers = [
        int((run.context_manifest or {}).get("latency", {}).get("provider_ms") or 0)
        for run in runs
        if isinstance(run.context_manifest, dict)
    ]
    providers = [item for item in providers if item]
    latest_latency = {}
    latest_manifest: dict[str, object] = {}
    if latest is not None and isinstance(latest.context_manifest, dict):
        latest_manifest = latest.context_manifest
        raw = latest_manifest.get("latency")
        latest_latency = raw if isinstance(raw, dict) else {}
    intent = latest_manifest.get("generation_intent")
    intent_key = str(intent) if intent else None
    requested = latest_manifest.get("requested_service_tier")
    returned = latest_manifest.get("returned_service_tier") or latest_manifest.get(
        "service_tier"
    )
    return {
        "latest_total_ms": None if latest is None else latest.latency_ms,
        "latest_provider_ms": latest_latency.get("provider_ms"),
        "latest_validation_ms": latest_latency.get("validation_ms"),
        "latest_attempts": (
            None
            if latest is None
            else latest_manifest.get("generation_attempt_count")
        ),
        "latest_input_tokens": None if latest is None else latest.input_tokens,
        "latest_output_tokens": None if latest is None else latest.output_tokens,
        "generation_intent": intent_key,
        "generation_intent_label": (
            None if intent_key is None else INTENT_LABELS.get(intent_key, intent_key)
        ),
        "reasoning_effort": latest_manifest.get("reasoning_effort"),
        "requested_service_tier": requested,
        "returned_service_tier": returned,
        "recent_count": len(runs),
        "median_total_ms": _median(totals),
        "median_provider_ms": _median(providers),
        "min_total_ms": min(totals) if totals else None,
        "max_total_ms": max(totals) if totals else None,
    }


def _focus_coach_preview(
    session: Session, child: Child
) -> tuple[str | None, tuple[str, ...]]:
    from daily_win_api.domains.daily_wins.context import prepare_daily_win_generation
    from daily_win_api.domains.daily_wins.schemas import ContextUnavailableError
    from daily_win_api.domains.learning.coach_protocol import protocol_from_dict
    from daily_win_api.domains.learning.explanations import display_name

    try:
        plan = prepare_daily_win_generation(session, child).plan
    except ContextUnavailableError:
        return None, ()
    protocol = protocol_from_dict(
        plan.coach_protocol if isinstance(plan.coach_protocol, dict) else None
    )
    card = protocol.coach_card if protocol is not None else ()
    return display_name(plan.primary_skill_code), tuple(card[:3])


def _stored_fingerprint(session: Session, win: DailyWin) -> str | None:
    if win.instruction_plan_id is None:
        return None
    row = session.get(InstructionPlanRecord, win.instruction_plan_id)
    if row is None or not isinstance(row.plan, dict):
        return None
    value = row.plan.get("plan_fingerprint")
    return str(value) if value else None


def _trigger_for_win(session: Session, win: DailyWin) -> str | None:
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    if run is None:
        return None
    return _trigger_from_manifest(run)


def _trigger_from_manifest(run: AiRun) -> str | None:
    manifest = run.context_manifest if isinstance(run.context_manifest, dict) else {}
    value = manifest.get("generation_trigger")
    return str(value) if value else None


def _stage_from_manifest(run: AiRun) -> str | None:
    manifest = run.context_manifest if isinstance(run.context_manifest, dict) else {}
    value = manifest.get("generation_stage")
    return str(value) if value else None


def _attempt_count_for_win(session: Session, win: DailyWin) -> int | None:
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    if run is None or not isinstance(run.context_manifest, dict):
        return None
    value = run.context_manifest.get("generation_attempt_count")
    return int(value) if value is not None else None


def _model_for_win(session: Session, win: DailyWin) -> str | None:
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    if run is None or run.model == "pending":
        return None
    return run.model


def _prompt_for_win(session: Session, win: DailyWin) -> str | None:
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    return None if run is None else run.prompt_version


def _latency_for_win(session: Session, win: DailyWin) -> int | None:
    run = session.get(AiRun, win.ai_run_id) if win.ai_run_id else None
    return None if run is None else run.latency_ms


def _latest_feedback(session: Session, child: Child) -> DailyWinFeedback | None:
    return session.scalars(
        select(DailyWinFeedback)
        .where(
            DailyWinFeedback.child_id == child.id,
            DailyWinFeedback.household_id == child.household_id,
        )
        .order_by(DailyWinFeedback.submitted_at.desc())
        .limit(1)
    ).first()


def _latest_win_any_status(session: Session, child: Child) -> DailyWin | None:
    return session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(1)
    ).first()


def _latest_run(session: Session, child: Child) -> AiRun | None:
    return session.scalars(
        select(AiRun)
        .where(AiRun.child_id == child.id, AiRun.household_id == child.household_id)
        .order_by(AiRun.started_at.desc())
        .limit(1)
    ).first()


def _median(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return int((ordered[mid - 1] + ordered[mid]) / 2)
