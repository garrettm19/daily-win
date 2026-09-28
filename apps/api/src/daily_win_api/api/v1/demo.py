import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from daily_win_api.ai.gateway import ModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.api.errors import SanitizedClientError
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, get_settings
from daily_win_api.db.session import get_db
from daily_win_api.dev.presets import (
    DIFFICULTY_SUGGESTIONS,
    DURATION_OPTIONS,
    GOAL_CATALOG,
    GRADE_OPTIONS,
    INTEREST_SUGGESTIONS,
    MAX_DIFFICULTIES,
    MAX_GOALS,
    MAX_INTERESTS,
    MAX_MOTIVATORS,
    MAX_STRENGTHS,
    MIN_GOALS,
    MOTIVATOR_SUGGESTIONS,
    RESPONSE_OPTIONS,
    STRENGTH_SUGGESTIONS,
)
from daily_win_api.dev.profile import (
    DemoProfileUpdate,
    DemoProfileWrite,
    ProfileSetupError,
    setup_custom_profile,
    setup_hayes_profile,
    update_demo_profile,
)
from daily_win_api.dev.reset import reset_demo_activity_history, restart_demo_session
from daily_win_api.dev.sessions import (
    DemoSessionRejectedError,
    DemoTenant,
    load_demo_session_row,
    resolve_demo_tenant,
    session_status,
)
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.children.queries import (
    DemoChildProfileUnavailableError,
    load_demo_child_profile,
)
from daily_win_api.domains.children.schemas import (
    DemoChildProfileRead,
    DemoOnboardingCatalog,
    DemoSessionRead,
)
from daily_win_api.domains.daily_wins.feedback import (
    FeedbackAlreadySubmittedError,
    FeedbackRejectedError,
    FeedbackUnavailableError,
    submit_demo_feedback,
)
from daily_win_api.domains.daily_wins.first_win import (
    first_win_timing_snapshot,
    record_guide_dwell,
)
from daily_win_api.domains.daily_wins.jobs import (
    schedule_prepare_after_profile_setup,
    schedule_prepare_after_reflection,
)
from daily_win_api.domains.daily_wins.latency import GenerationTimer
from daily_win_api.domains.daily_wins.preparation import (
    TRIGGER_FIRST_PROFILE_SETUP,
    mark_preparation_started,
    read_next_win_preparation,
)
from daily_win_api.domains.daily_wins.queries import (
    get_demo_daily_win,
    get_latest_demo_daily_win,
)
from daily_win_api.domains.daily_wins.schemas import (
    CLIENT_ALREADY_CONFIGURED,
    CLIENT_FEEDBACK_EXISTS,
    CLIENT_FEEDBACK_FAILED,
    CLIENT_FEEDBACK_NOT_FOUND,
    CLIENT_GENERATION_FAILED,
    CLIENT_NOT_FOUND,
    CLIENT_RESET_FAILED,
    CLIENT_SETUP_REQUIRED,
    CLIENT_UNAVAILABLE,
    ContextUnavailableError,
    DailyWinFeedbackCreate,
    DailyWinGenerationError,
    DemoDailyWinRead,
    DemoFeedbackRead,
    DemoResetRead,
    FirstWinTimingRead,
    GuideTimingWrite,
    NextWinStateRead,
    PilotStatusRead,
    WeeklyCoachReportRead,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win
from daily_win_api.domains.learning.observatory import (
    build_curriculum_graph,
    build_learner_snapshot,
    build_learning_qa,
    build_learning_trace,
    build_next_win_preview,
    build_redacted_context,
    engine_version_report,
)
from daily_win_api.domains.learning.observatory_schemas import (
    CurriculumGraphTrace,
    EngineVersionReport,
    LearnerSnapshot,
    LearningQaBundle,
    LearningTrace,
    NextWinPreview,
    RedactedContextReport,
)
from daily_win_api.domains.learning.progress import (
    DemoDailyWinSummary,
    DemoProgressRead,
    list_demo_daily_win_summaries,
    load_demo_progress,
)
from daily_win_api.domains.learning.weekly_query import load_weekly_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


def get_demo_tenant(
    db: Annotated[Session, Depends(get_db)],
    x_demo_session: Annotated[str | None, Header(alias="X-Demo-Session")] = None,
) -> DemoTenant:
    """Resolve the isolated synthetic tenant. Not production authorization."""
    try:
        return resolve_demo_tenant(db, x_demo_session)
    except DemoSessionRejectedError:
        raise SanitizedClientError(
            status_code=400,
            detail=CLIENT_UNAVAILABLE,
            error_code="demo_unavailable",
        ) from None


def require_configured_child(tenant: DemoTenant) -> Child:
    if tenant.child is None:
        raise SanitizedClientError(
            status_code=409,
            detail=CLIENT_SETUP_REQUIRED,
            error_code="setup_required",
        )
    return tenant.child


def _begin_first_win_preparation(
    db: Session, child_id: UUID, background_tasks: BackgroundTasks
) -> None:
    from daily_win_api.domains.daily_wins import jobs as win_jobs

    if not win_jobs.BACKGROUND_PREGENERATE_ENABLED:
        return
    child = db.get(Child, child_id)
    if child is None:
        return
    mark_preparation_started(db, child, TRIGGER_FIRST_PROFILE_SETUP)
    db.commit()
    schedule_prepare_after_profile_setup(child.id, background_tasks.add_task)


@router.get("/session", response_model=DemoSessionRead)
def read_demo_session(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoSessionRead:
    """Development/demo only. Not production authorization."""
    profile = None
    if tenant.child is not None:
        try:
            profile = load_demo_child_profile(
                db, tenant.child, tester_fingerprint=tenant.tester_fingerprint
            )
        except DemoChildProfileUnavailableError:
            profile = None
    db.commit()
    return DemoSessionRead(
        status=session_status(tenant),
        profile_source=tenant.profile_source,
        tester_fingerprint=tenant.tester_fingerprint,
        profile=profile,
    )


@router.get("/onboarding-catalog", response_model=DemoOnboardingCatalog)
def read_onboarding_catalog(
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoOnboardingCatalog:
    """Development/demo only. Synthetic onboarding options."""
    return DemoOnboardingCatalog(
        grades=[dict(item) for item in GRADE_OPTIONS],
        interest_suggestions=list(INTEREST_SUGGESTIONS),
        strength_suggestions=list(STRENGTH_SUGGESTIONS),
        difficulty_suggestions=list(DIFFICULTY_SUGGESTIONS),
        response_options=list(RESPONSE_OPTIONS),
        motivator_suggestions=list(MOTIVATOR_SUGGESTIONS),
        durations=list(DURATION_OPTIONS),
        goals=[dict(item) for item in GOAL_CATALOG],
        min_goals=MIN_GOALS,
        max_goals=MAX_GOALS,
        max_interests=MAX_INTERESTS,
        max_strengths=MAX_STRENGTHS,
        max_difficulties=MAX_DIFFICULTIES,
        max_motivators=MAX_MOTIVATORS,
    )


@router.post("/setup/hayes", response_model=DemoChildProfileRead)
def create_hayes_demo_profile(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
    background_tasks: BackgroundTasks,
) -> DemoChildProfileRead:
    """Development/demo only. One-tap synthetic Hayes profile."""
    try:
        profile = setup_hayes_profile(db, tenant)
        db.commit()
        _begin_first_win_preparation(db, profile.child.id, background_tasks)
        return profile
    except ProfileSetupError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=(
                CLIENT_ALREADY_CONFIGURED
                if exc.code == "already_configured"
                else CLIENT_UNAVAILABLE
            ),
            error_code=exc.code,
        ) from None


@router.post("/setup/profile", response_model=DemoChildProfileRead)
def create_custom_demo_profile(
    payload: DemoProfileWrite,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
    background_tasks: BackgroundTasks,
) -> DemoChildProfileRead:
    """Development/demo only. Custom synthetic profile."""
    try:
        profile = setup_custom_profile(db, tenant, payload)
        db.commit()
        _begin_first_win_preparation(db, profile.child.id, background_tasks)
        return profile
    except ProfileSetupError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=(
                CLIENT_ALREADY_CONFIGURED
                if exc.code == "already_configured"
                else CLIENT_UNAVAILABLE
            ),
            error_code=exc.code,
        ) from None


@router.patch("/profile", response_model=DemoChildProfileRead)
def patch_demo_profile(
    payload: DemoProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoChildProfileRead:
    """Development/demo only. Versioned baseline + auditable goal update."""
    try:
        profile = update_demo_profile(db, tenant, payload)
        db.commit()
        return profile
    except ProfileSetupError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=(
                CLIENT_SETUP_REQUIRED
                if exc.code == "setup_required"
                else CLIENT_UNAVAILABLE
            ),
            error_code=exc.code,
        ) from None


@router.get("/child-profile", response_model=DemoChildProfileRead)
def read_demo_child_profile(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoChildProfileRead:
    """Development/demo only. Not production authorization."""
    child = require_configured_child(tenant)
    try:
        profile = load_demo_child_profile(
            db, child, tester_fingerprint=tenant.tester_fingerprint
        )
        db.commit()
        return profile
    except DemoChildProfileUnavailableError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Demo child profile is not available.",
        ) from None


@router.get("/progress", response_model=DemoProgressRead)
def read_demo_progress(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoProgressRead:
    """Development/demo only. Cautious parent-facing progress."""
    child = require_configured_child(tenant)
    result = load_demo_progress(db, child)
    db.commit()
    return result


@router.get("/daily-wins", response_model=list[DemoDailyWinSummary])
def list_demo_daily_wins(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> list[DemoDailyWinSummary]:
    """Development/demo only. Newest first."""
    child = require_configured_child(tenant)
    result = list_demo_daily_win_summaries(db, child)
    db.commit()
    return result


@router.post("/daily-wins/generate", response_model=DemoDailyWinRead)
def create_demo_daily_win(
    db: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoDailyWinRead:
    """Development/demo only. Not production authorization."""
    child = require_configured_child(tenant)
    try:
        result = generate_demo_daily_win(db, gateway, child)
        db.commit()
        return result
    except DailyWinGenerationError as exc:
        db.commit()
        detail = (
            exc.client_message
            if exc.http_status in {404, 409}
            else CLIENT_GENERATION_FAILED
        )
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=detail,
            error_code=exc.code,
            dev_reason=exc.dev_reason,
        ) from None


@router.get("/daily-wins/latest", response_model=DemoDailyWinRead)
def read_latest_demo_daily_win(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoDailyWinRead:
    """Development/demo only. Not production authorization."""
    child = require_configured_child(tenant)
    db.commit()
    result = get_latest_demo_daily_win(db, child)
    if result is None:
        raise HTTPException(status_code=404, detail="No Daily Win is available yet.")
    return result


@router.get("/next-win-state", response_model=NextWinStateRead)
def read_next_win_state(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> NextWinStateRead:
    """Home load: READY Win, preparation status, or first-win preview. No OpenAI."""
    timer = GenerationTimer()
    child = require_configured_child(tenant)
    prep = read_next_win_preparation(db, child)
    timing = first_win_timing_snapshot(db, child)
    db.commit()
    logger.info(
        "HOME TRACE total=%sms status=%s has_ready=%s model_call=no",
        timer.total_ms(),
        prep.status,
        prep.daily_win is not None,
    )
    logger.info(
        "FIRST WIN TRACE profile_saved=%sms prep_started=+%sms "
        "terra_completed=+%sms win_ready=+%sms raw_model=%sms",
        timing.get("profile_saved_ms"),
        timing.get("preparation_started_ms"),
        timing.get("terra_completed_ms"),
        timing.get("win_ready_ms"),
        timing.get("raw_model_ms"),
    )
    return NextWinStateRead(
        daily_win=prep.daily_win,
        preparation_status=prep.status,
        trigger=prep.trigger,
        generation_stage=prep.generation_stage,
        focus_preview=prep.focus_preview,
        coach_preview=list(prep.coach_preview),
        generated_after_reflection=prep.generated_after_reflection,
        plan_valid=prep.plan_valid,
        error_code=prep.error_code,
        attempt_count=prep.attempt_count,
        model=prep.model,
        prompt_version=prep.prompt_version,
        latency_ms=prep.latency_ms,
        backend_elapsed_ms=timer.total_ms(),
        first_win_timing=FirstWinTimingRead.model_validate(timing),
    )


@router.get("/daily-wins/{daily_win_id}", response_model=DemoDailyWinRead)
def read_demo_daily_win(
    daily_win_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoDailyWinRead:
    """Development/demo only. Session-owned Daily Win, or 404."""
    child = require_configured_child(tenant)
    result = get_demo_daily_win(db, daily_win_id, child)
    db.commit()
    if result is None:
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND)
    return result


@router.post(
    "/daily-wins/{daily_win_id}/feedback",
    response_model=DemoFeedbackRead,
)
def create_demo_daily_win_feedback(
    daily_win_id: UUID,
    payload: DailyWinFeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
    background_tasks: BackgroundTasks,
) -> DemoFeedbackRead:
    """Development/demo only. Not production authorization."""
    child = require_configured_child(tenant)
    try:
        result = submit_demo_feedback(db, daily_win_id, payload, child)
        db.commit()
        schedule_prepare_after_reflection(child.id, background_tasks.add_task)
        return result
    except FeedbackUnavailableError:
        db.rollback()
        raise SanitizedClientError(
            status_code=404,
            detail=CLIENT_FEEDBACK_NOT_FOUND,
            error_code="demo_unavailable",
        ) from None
    except FeedbackAlreadySubmittedError:
        db.rollback()
        raise SanitizedClientError(
            status_code=409,
            detail=CLIENT_FEEDBACK_EXISTS,
            error_code="already_submitted",
        ) from None
    except FeedbackRejectedError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=422,
            detail=CLIENT_FEEDBACK_FAILED,
            error_code=exc.code,
        ) from None
    except DailyWinGenerationError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=CLIENT_FEEDBACK_FAILED,
            error_code=exc.code,
        ) from None
    except Exception as exc:
        logger.error("Demo feedback submission failed (%s)", type(exc).__name__)
        db.rollback()
        raise SanitizedClientError(
            status_code=500,
            detail=CLIENT_FEEDBACK_FAILED,
            error_code="provider_error",
        ) from None


@router.get("/weekly-report", response_model=WeeklyCoachReportRead)
def read_weekly_coach_report(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> WeeklyCoachReportRead:
    """Development/demo only. Deterministic weekly synthesis from evidence."""
    child = require_configured_child(tenant)
    summary = load_weekly_summary(db, child)
    db.commit()
    payload = summary.as_dict()
    return WeeklyCoachReportRead.model_validate(payload)


@router.post("/reset", response_model=DemoResetRead)
@router.post("/reset/activity", response_model=DemoResetRead)
def reset_demo_activity(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoResetRead:
    """Development/demo only. Clears activity history. Profile remains."""
    try:
        if tenant.child is not None:
            reset_demo_activity_history(
                db,
                child_id=tenant.child.id,
                household_id=tenant.child.household_id,
            )
        db.commit()
        return DemoResetRead(mode="activity")
    except Exception as exc:
        logger.error("Demo activity reset failed (%s)", type(exc).__name__)
        db.rollback()
        raise SanitizedClientError(
            status_code=500,
            detail=CLIENT_RESET_FAILED,
            error_code="provider_error",
        ) from None


@router.post("/reset/session", response_model=DemoResetRead)
def reset_demo_from_beginning(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> DemoResetRead:
    """Development/demo only. Returns this session to first-run."""
    try:
        row = load_demo_session_row(db, tenant.session_hash)
        if row is not None:
            restart_demo_session(db, row)
        db.commit()
        return DemoResetRead(mode="session")
    except Exception as exc:
        logger.error("Demo session restart failed (%s)", type(exc).__name__)
        db.rollback()
        raise SanitizedClientError(
            status_code=500,
            detail=CLIENT_RESET_FAILED,
            error_code="provider_error",
        ) from None


@router.get("/pilot/status", response_model=PilotStatusRead)
def read_pilot_status(
    db: Annotated[Session, Depends(get_db)],
) -> PilotStatusRead:
    """Development-only non-sensitive preflight. Never returns secrets."""
    db_ok = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = "unavailable"
    settings = get_settings()
    engine = engine_version_report()
    prep_available = "unavailable"
    try:
        from daily_win_api.domains.daily_wins.preparation import NextWinPreparation

        assert NextWinPreparation is not None
        prep_available = "available"
    except Exception:
        prep_available = "unavailable"
    return PilotStatusRead(
        api="ok",
        db=db_ok,
        generation_config="configured" if settings.openai_configured else "missing",
        model=settings.openai_model or DEFAULT_OPENAI_MODEL,
        curriculum=engine.curriculum_version,
        placement=engine.placement_policy,
        scheduler=engine.instruction_scheduler,
        instruction=engine.instruction_policy,
        prompt=engine.prompt_version,
        background_preparation=prep_available,
    )


@router.post("/pilot/guide-timing")
def write_guide_timing(
    payload: GuideTimingWrite,
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> dict[str, object]:
    """Development-only Guide dwell. Not learner evidence and not analytics."""
    child = require_configured_child(tenant)
    dwell = payload.guide_dwell_ms
    if (
        dwell is None
        and payload.guide_started_at is not None
        and payload.guide_finished_at is not None
    ):
        dwell = max(
            0,
            int(
                (payload.guide_finished_at - payload.guide_started_at).total_seconds()
                * 1000
            ),
        )
    record_guide_dwell(
        child.id,
        dwell_ms=dwell or 0,
        skipped=payload.guide_skipped,
        started_at=(
            None
            if payload.guide_started_at is None
            else payload.guide_started_at.isoformat()
        ),
        finished_at=(
            None
            if payload.guide_finished_at is None
            else payload.guide_finished_at.isoformat()
        ),
    )
    return {"ok": True}


@router.get("/observatory/engine-versions", response_model=EngineVersionReport)
def read_engine_versions() -> EngineVersionReport:
    """Development/demo only. Policy and renderer version inventory."""
    return engine_version_report()


@router.get("/observatory/learning-qa", response_model=LearningQaBundle)
def read_learning_qa(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> LearningQaBundle:
    """Development/demo only. Mason's backend-debug bundle."""
    if tenant.child is None:
        return LearningQaBundle(
            engine=engine_version_report(),
            snapshot=LearnerSnapshot(
                nickname="(setup required)", academic=[], growth=[]
            ),
            graph=CurriculumGraphTrace(strand="", target_skill=None, nodes=[]),
            setup_required=True,
        )
    result = build_learning_qa(db, tenant.child)
    db.commit()
    return result


@router.get("/observatory/learning-trace", response_model=LearningTrace)
def read_latest_learning_trace(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> LearningTrace:
    """Development/demo only. Authoritative Learning Trace for the latest Win."""
    child = require_configured_child(tenant)
    try:
        result = build_learning_trace(db, child)
        db.commit()
        return result
    except ContextUnavailableError:
        db.rollback()
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND) from None


@router.get("/observatory/learning-trace/{daily_win_id}", response_model=LearningTrace)
def read_learning_trace(
    daily_win_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> LearningTrace:
    """Development/demo only. Authoritative Learning Trace for one Win."""
    child = require_configured_child(tenant)
    try:
        result = build_learning_trace(db, child, daily_win_id)
        db.commit()
        return result
    except ContextUnavailableError:
        db.rollback()
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND) from None


@router.get("/observatory/learner-snapshot", response_model=LearnerSnapshot)
def read_learner_snapshot(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> LearnerSnapshot:
    """Development/demo only. Derived learner snapshot without raw DB rows."""
    child = require_configured_child(tenant)
    result = build_learner_snapshot(db, child)
    db.commit()
    return result


@router.get("/observatory/curriculum-graph", response_model=CurriculumGraphTrace)
def read_curriculum_graph(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> CurriculumGraphTrace:
    """Development/demo only. Relevant strand graph with learner position."""
    child = require_configured_child(tenant)
    try:
        result = build_curriculum_graph(db, child)
        db.commit()
        return result
    except ContextUnavailableError:
        db.rollback()
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND) from None


@router.get("/observatory/next-win-preview", response_model=NextWinPreview)
def read_next_win_preview(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> NextWinPreview:
    """Development/demo only. Planner preview. Does not create a Win."""
    child = require_configured_child(tenant)
    try:
        result = build_next_win_preview(db, child)
        db.commit()
        return result
    except ContextUnavailableError:
        db.rollback()
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND) from None


@router.get("/observatory/renderer-context", response_model=RedactedContextReport)
def read_redacted_renderer_context(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[DemoTenant, Depends(get_demo_tenant)],
) -> RedactedContextReport:
    """Development/demo only. Bounded, redacted renderer context."""
    child = require_configured_child(tenant)
    try:
        result = build_redacted_context(db, child)
        db.commit()
        return result
    except ContextUnavailableError:
        db.rollback()
        raise HTTPException(status_code=404, detail=CLIENT_NOT_FOUND) from None
