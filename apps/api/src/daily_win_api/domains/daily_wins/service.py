import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.decision import DecisionGateway, VerificationResult
from daily_win_api.ai.decision.policy import Verdict, combine_verification
from daily_win_api.ai.delivery import (
    bind_delivery,
    delivery_for_intent,
    infer_generation_intent,
)
from daily_win_api.ai.error_codes import sanitize_error_code
from daily_win_api.ai.exceptions import (
    ModelGatewayConfigurationError,
    ModelGatewayError,
    ModelGatewaySchemaError,
)
from daily_win_api.ai.gateway import ModelGateway
from daily_win_api.ai.moderation import (
    ModerationRejectedError,
    review_generated_daily_win,
)
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import DailyWinDraft, DailyWinGenerationResult
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.context import prepare_daily_win_generation
from daily_win_api.domains.daily_wins.fingerprint import (
    compute_plan_fingerprint,
    fingerprints_match,
)
from daily_win_api.domains.daily_wins.latency import (
    GenerationTimer,
    bind_timer,
    log_generation_trace,
)
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.queries import to_demo_daily_win_read
from daily_win_api.domains.daily_wins.renderer_contract import (
    validate_renderer_contract,
)
from daily_win_api.domains.daily_wins.safety import validate_daily_win_safety
from daily_win_api.domains.daily_wins.schemas import (
    AI_RUN_STATUS_FAILED,
    AI_RUN_STATUS_REJECTED,
    AI_RUN_STATUS_STARTED,
    AI_RUN_STATUS_SUCCEEDED,
    CLIENT_FEEDBACK_REQUIRED,
    CLIENT_GENERATION_FAILED,
    CLIENT_GENERATION_IN_PROGRESS,
    CLIENT_UNAVAILABLE,
    CONTENT_SCHEMA_VERSION,
    DAILY_WIN_STATUS_READY,
    INPUT_SCHEMA_VERSION,
    MAX_GENERATION_ATTEMPTS,
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    ContextUnavailableError,
    DailyWinGenerationError,
    DemoDailyWinRead,
    RendererContractError,
    SafetyRejectedError,
    SkillContractError,
)
from daily_win_api.domains.learning.models import (
    DecisionRun,
    InstructionPlanRecord,
    Skill,
)
from daily_win_api.domains.learning.planner import InstructionPlan, plan_as_dict
from daily_win_api.domains.learning.presentation import what_changed_today

logger = logging.getLogger(__name__)


def generate_demo_daily_win(
    session: Session,
    gateway: ModelGateway,
    child: Child | None = None,
    decision_gateway: DecisionGateway | None = None,
    *,
    trigger: str | None = None,
    max_attempts: int | None = None,
    commit_started: bool = False,
) -> DemoDailyWinRead:
    timer = GenerationTimer()
    with bind_timer(timer):
        return _generate_demo_daily_win(
            session,
            gateway,
            child,
            decision_gateway,
            trigger=trigger,
            max_attempts=max_attempts,
            timer=timer,
            commit_started=commit_started,
        )


def _generate_demo_daily_win(
    session: Session,
    gateway: ModelGateway,
    child: Child | None,
    decision_gateway: DecisionGateway | None,
    *,
    trigger: str | None,
    max_attempts: int | None,
    timer: GenerationTimer,
    commit_started: bool,
) -> DemoDailyWinRead:
    with timer.span("session_lookup_ms"):
        resolved = child or get_demo_child(session)
        if resolved is None:
            raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)
        locked = session.scalars(
            select(Child).where(Child.id == resolved.id).with_for_update()
        ).first()
        if locked is None:
            raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)
        resolved = locked

    from daily_win_api.domains.daily_wins.preparation import (
        TRIGGER_FIRST_PROFILE_SETUP,
        TRIGGER_FIRST_RUN,
        TRIGGER_MANUAL,
        TRIGGER_REFLECTION,
        unreflected_ready_win,
    )
    STALE_STARTED_SECONDS = 180

    existing = unreflected_ready_win(session, resolved)
    if existing is not None:
        if trigger in {TRIGGER_REFLECTION, TRIGGER_FIRST_PROFILE_SETUP}:
            skill = session.get(Skill, existing.primary_skill_id)
            if skill is None:
                raise DailyWinGenerationError(
                    "unknown_skill", 422, CLIENT_GENERATION_FAILED
                )
            return to_demo_daily_win_read(
                session, existing, skill, resolved.nickname
            )
        raise DailyWinGenerationError(
            "feedback_required", 409, CLIENT_FEEDBACK_REQUIRED
        )

    in_flight = session.scalars(
        select(AiRun)
        .where(
            AiRun.child_id == resolved.id,
            AiRun.household_id == resolved.household_id,
            AiRun.status == AI_RUN_STATUS_STARTED,
            AiRun.completed_at.is_(None),
        )
        .order_by(AiRun.started_at.desc())
        .limit(1)
    ).first()
    if in_flight is not None:
        started = in_flight.started_at
        age = (
            (datetime.now(UTC) - started).total_seconds()
            if started is not None
            else STALE_STARTED_SECONDS
        )
        prep_job = trigger in {TRIGGER_REFLECTION, TRIGGER_FIRST_PROFILE_SETUP}
        if age < STALE_STARTED_SECONDS and not prep_job:
            raise DailyWinGenerationError(
                "generation_in_progress",
                409,
                CLIENT_GENERATION_IN_PROGRESS,
            )
        in_flight.status = AI_RUN_STATUS_FAILED
        in_flight.error_code = "superseded"
        in_flight.completed_at = datetime.now(UTC)

    try:
        with timer.span("context_build_ms"):
            prep = prepare_daily_win_generation(session, resolved)
    except ContextUnavailableError:
        raise DailyWinGenerationError(
            "demo_unavailable", 404, CLIENT_UNAVAILABLE
        ) from None

    if trigger is None:
        prior = session.scalar(
            select(DailyWin.id).where(
                DailyWin.child_id == resolved.id,
                DailyWin.household_id == resolved.household_id,
                DailyWin.status == DAILY_WIN_STATUS_READY,
            )
        )
        trigger = TRIGGER_FIRST_RUN if prior is None else TRIGGER_MANUAL

    intent = infer_generation_intent(
        trigger=trigger, commit_started=commit_started
    )
    delivery = delivery_for_intent(intent)
    gateway = bind_delivery(gateway, delivery)

    plan_skill = session.scalar(
        select(Skill).where(Skill.code == prep.plan.primary_skill_code)
    )
    if plan_skill is None:
        raise DailyWinGenerationError("unknown_skill", 422, CLIENT_GENERATION_FAILED)

    fingerprint = compute_plan_fingerprint(session, resolved)
    now = datetime.now(UTC)
    run = AiRun(
        id=uuid4(),
        household_id=resolved.household_id,
        child_id=resolved.id,
        operation=OPERATION_DAILY_WIN_GENERATE,
        provider="pending",
        model="pending",
        prompt_version=PROMPT_VERSION,
        input_schema_version=INPUT_SCHEMA_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        status=AI_RUN_STATUS_STARTED,
        context_manifest={
            **prep.manifest.model_dump(mode="json"),
            "generation_trigger": trigger,
            "generation_stage": "building_challenge",
            "plan_fingerprint": fingerprint,
            "generation_intent": delivery.intent,
            "requested_service_tier": delivery.requested_service_tier,
            "reasoning_effort": delivery.reasoning_effort,
        },
        started_at=now,
    )
    session.add(run)
    session.flush()
    if commit_started:
        session.commit()
        session.refresh(run)
        locked_again = session.scalars(
            select(Child).where(Child.id == resolved.id).with_for_update()
        ).first()
        if locked_again is not None:
            resolved = locked_again

    allowed_codes = set(prep.context.allowed_skill_codes)
    last_reject: Exception | None = None
    last_verification: VerificationResult | None = None
    result: DailyWinGenerationResult | None = None
    attempts = 0
    limit = max_attempts or MAX_GENERATION_ATTEMPTS
    for _attempt in range(limit):
        attempts += 1
        try:
            with timer.span("provider_ms"):
                result = gateway.generate_daily_win(prep.context)
        except ModelGatewayConfigurationError as exc:
            code = sanitize_error_code(exc.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_FAILED,
                error_code=code,
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(code, 503, CLIENT_GENERATION_FAILED) from None
        except ModelGatewaySchemaError as exc:
            logger.error("Daily Win schema failure (%s)", type(exc).__name__)
            code = sanitize_error_code(exc.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_FAILED,
                error_code=code,
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(code, 502, CLIENT_GENERATION_FAILED) from None
        except ModelGatewayError as exc:
            logger.error("Daily Win provider failure (%s)", type(exc).__name__)
            code = sanitize_error_code(exc.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_FAILED,
                error_code=code,
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(code, 502, CLIENT_GENERATION_FAILED) from None
        except Exception:
            logger.error("Daily Win generation failed (%s)", "Exception")
            _complete_run(
                run,
                status=AI_RUN_STATUS_FAILED,
                error_code="provider_error",
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(
                "provider_error", 502, CLIENT_GENERATION_FAILED
            ) from None

        _apply_result_metadata(run, result)
        try:
            with timer.span("validation_ms"):
                _validate_skill_contract(result.draft, allowed_codes, prep.plan)
                validate_renderer_contract(result.draft, prep.plan)
                validate_daily_win_safety(result.draft)
                review_generated_daily_win(result.draft)
                if decision_gateway is not None:
                    verification = decision_gateway.evaluate_activity(
                        prep.plan, result.draft, tuple(prep.context.recent_themes)
                    )
                    verdict = combine_verification(verification)
                    if verdict is Verdict.FAIL:
                        raise SkillContractError("verification_failed")
                    if verdict is Verdict.UNCERTAIN:
                        raise SkillContractError("verification_uncertain")
                    last_verification = verification
        except SkillContractError as exc:
            last_reject = exc
            continue
        except RendererContractError as exc:
            last_reject = exc
            continue
        except SafetyRejectedError as exc:
            last_reject = exc
            continue
        except ModerationRejectedError as exc:
            last_reject = exc
            continue
        break
    else:
        assert last_reject is not None
        assert result is not None
        if isinstance(last_reject, SafetyRejectedError):
            code = sanitize_error_code(last_reject.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_REJECTED,
                error_code=code,
                result=result,
                attempt_count=attempts,
                safety_rule=last_reject.rule,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(
                code,
                422,
                CLIENT_GENERATION_FAILED,
                dev_reason=last_reject.rule,
            ) from None
        if isinstance(last_reject, RendererContractError):
            code = sanitize_error_code(last_reject.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_REJECTED,
                error_code=code,
                result=result,
                attempt_count=attempts,
                failed_contracts=last_reject.failed_contracts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(
                code,
                422,
                CLIENT_GENERATION_FAILED,
                dev_reason=last_reject.rule,
            ) from None
        if isinstance(last_reject, ModerationRejectedError):
            code = sanitize_error_code(last_reject.code)
            _complete_run(
                run,
                status=AI_RUN_STATUS_REJECTED,
                error_code=code,
                result=result,
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
            raise DailyWinGenerationError(code, 422, CLIENT_GENERATION_FAILED) from None
        code = sanitize_error_code(last_reject.code)
        _complete_run(
            run,
            status=AI_RUN_STATUS_REJECTED,
            error_code=code,
            result=result,
            attempt_count=attempts,
            timer=timer,
            trigger=trigger,
        )
        session.flush()
        raise DailyWinGenerationError(code, 422, CLIENT_GENERATION_FAILED) from None

    assert result is not None
    if not _generation_still_wanted(
        session,
        run_id=run.id,
        child_id=resolved.id,
        expected_fingerprint=fingerprint,
    ):
        run = session.get(AiRun, run.id)
        if run is not None and run.status == AI_RUN_STATUS_STARTED:
            _complete_run(
                run,
                status=AI_RUN_STATUS_FAILED,
                error_code="superseded",
                attempt_count=attempts,
                timer=timer,
                trigger=trigger,
            )
            session.flush()
        raise DailyWinGenerationError(
            "superseded", 409, CLIENT_GENERATION_FAILED
        )
    run = session.get(AiRun, run.id)
    resolved_child = session.get(Child, resolved.id)
    if run is None or resolved_child is None:
        raise DailyWinGenerationError(
            "superseded", 409, CLIENT_GENERATION_FAILED
        )
    resolved = resolved_child
    refreshed_skill = session.get(Skill, plan_skill.id)
    if refreshed_skill is not None:
        plan_skill = refreshed_skill
    draft = result.draft
    if not prep.context.recent_themes:
        draft = draft.model_copy(update={"adaptation_summary": None})
    elif not draft.adaptation_summary:
        changed = what_changed_today(
            has_prior_wins=True,
            skill_display_name=plan_skill.display_name,
            reason_codes=prep.plan.selection_reason_codes,
            instruction_mode=prep.plan.instruction_mode.value,
            scaffold=prep.plan.scaffold_level.value,
            growth_summary=prep.plan.growth_adaptation_summary,
        )
        if changed:
            draft = draft.model_copy(update={"adaptation_summary": changed})

    with timer.span("persistence_ms"):
        plan_payload = plan_as_dict(prep.plan)
        plan_payload["plan_fingerprint"] = fingerprint
        plan_payload["generated_after_reflection"] = trigger == TRIGGER_REFLECTION
        plan_row = InstructionPlanRecord(
            id=uuid4(),
            household_id=resolved.household_id,
            child_id=resolved.id,
            primary_skill_id=plan_skill.id,
            policy_version=prep.plan.policy_version,
            instruction_mode=prep.plan.instruction_mode.value,
            scaffold_level=prep.plan.scaffold_level.value,
            reason_codes=list(prep.plan.selection_reason_codes),
            plan=plan_payload,
        )
        session.add(plan_row)
        session.flush()
        if last_verification is not None:
            _persist_decision_run(
                session,
                resolved=resolved,
                plan_row=plan_row,
                verification=last_verification,
            )

        daily_win = DailyWin(
            id=uuid4(),
            household_id=resolved.household_id,
            child_id=resolved.id,
            primary_skill_id=plan_skill.id,
            ai_run_id=run.id,
            instruction_plan_id=plan_row.id,
            title=draft.title,
            objective=draft.objective,
            duration_minutes=draft.duration_minutes,
            content=draft.model_dump(mode="json"),
            content_schema_version=CONTENT_SCHEMA_VERSION,
            status=DAILY_WIN_STATUS_READY,
            created_at=datetime.now(UTC),
        )
        session.add(daily_win)
        _complete_run(
            run,
            status=AI_RUN_STATUS_SUCCEEDED,
            result=result,
            attempt_count=attempts,
            timer=timer,
            trigger=trigger,
        )
        session.flush()
    return to_demo_daily_win_read(session, daily_win, plan_skill, resolved.nickname)


def _generation_still_wanted(
    session: Session,
    *,
    run_id,
    child_id,
    expected_fingerprint: str,
) -> bool:
    """Abort persist if reset or a relevant profile edit superseded this run."""
    session.expire_all()
    child = session.get(Child, child_id)
    if child is None:
        return False
    run = session.get(AiRun, run_id)
    if run is None or run.status != AI_RUN_STATUS_STARTED:
        return False
    current = compute_plan_fingerprint(session, child)
    return fingerprints_match(expected_fingerprint, current)


def _validate_skill_contract(
    draft: DailyWinDraft, allowed_codes: set[str], plan: InstructionPlan
) -> None:
    if draft.primary_skill_code not in allowed_codes:
        raise SkillContractError("unknown_skill")
    if draft.primary_skill_code != plan.primary_skill_code:
        raise SkillContractError("instruction_plan_mismatch")
    permitted_support = {
        code for code in (plan.supporting_skill_code, plan.growth_target_code) if code
    }
    for code in draft.supporting_skill_codes:
        if code not in allowed_codes:
            raise SkillContractError("unknown_skill")
        if permitted_support and code not in permitted_support | {
            plan.primary_skill_code
        }:
            raise SkillContractError("instruction_plan_mismatch")


def _persist_decision_run(
    session: Session,
    *,
    resolved: Child,
    plan_row: InstructionPlanRecord,
    verification: VerificationResult,
) -> None:
    confidences = [item.confidence for item in verification.decisions]
    mean = sum(confidences) / len(confidences) if confidences else None
    session.add(
        DecisionRun(
            household_id=resolved.household_id,
            child_id=resolved.id,
            operation="activity_verification",
            provider=verification.provider,
            model=verification.model,
            schema_version=verification.schema_version,
            output={
                "decisions": [
                    {
                        "name": item.name,
                        "value": item.value,
                        "confidence": item.confidence,
                        "safety_critical": item.safety_critical,
                    }
                    for item in verification.decisions
                ]
            },
            confidence=mean,
            instruction_plan_id=plan_row.id,
        )
    )
    session.flush()


def _apply_result_metadata(run: AiRun, result: DailyWinGenerationResult) -> None:
    run.provider = result.provider
    run.model = result.model
    run.prompt_version = result.prompt_version
    run.provider_request_id = result.provider_request_id
    run.input_tokens = result.input_tokens
    run.output_tokens = result.output_tokens
    run.total_tokens = result.total_tokens
    run.latency_ms = result.latency_ms


def _complete_run(
    run: AiRun,
    *,
    status: str,
    error_code: str | None = None,
    result: DailyWinGenerationResult | None = None,
    attempt_count: int | None = None,
    failed_contracts: tuple[str, ...] | None = None,
    safety_rule: str | None = None,
    timer: GenerationTimer | None = None,
    trigger: str | None = None,
) -> None:
    if result is not None:
        _apply_result_metadata(run, result)
    run.status = status
    run.error_code = error_code
    run.completed_at = datetime.now(UTC)
    manifest = dict(run.context_manifest or {})
    if attempt_count is not None:
        manifest["generation_attempt_count"] = attempt_count
    if trigger:
        manifest["generation_trigger"] = trigger
    if timer is not None:
        timings = timer.as_dict()
        if result is not None and result.latency_ms is not None:
            timings["provider_ms"] = result.latency_ms
        manifest["latency"] = timings
        log_generation_trace(
            timings=timings,
            model=run.model,
            prompt_version=run.prompt_version,
            attempts=attempt_count or 1,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            cached_input_tokens=(
                None if result is None else result.cached_input_tokens
            ),
            service_tier=None if result is None else result.service_tier,
            requested_service_tier=(
                None if result is None else result.requested_service_tier
            ),
            reasoning_effort=None if result is None else result.reasoning_effort,
            generation_intent=None if result is None else result.generation_intent,
            trigger=trigger or "manual",
        )
    if result is not None:
        if result.cached_input_tokens is not None:
            manifest["cached_input_tokens"] = result.cached_input_tokens
        if result.reasoning_tokens is not None:
            manifest["reasoning_tokens"] = result.reasoning_tokens
        if result.service_tier:
            manifest["service_tier"] = result.service_tier
            manifest["returned_service_tier"] = result.service_tier
        if result.requested_service_tier:
            manifest["requested_service_tier"] = result.requested_service_tier
        if result.reasoning_effort:
            manifest["reasoning_effort"] = result.reasoning_effort
        if result.generation_intent:
            manifest["generation_intent"] = result.generation_intent
    if error_code or failed_contracts or safety_rule:
        manifest["generation_failure"] = {
            "api_code": error_code,
            "attempt_count": attempt_count,
            "failed_contracts": list(failed_contracts or ()),
            "safety_rule": safety_rule,
        }
    run.context_manifest = manifest
