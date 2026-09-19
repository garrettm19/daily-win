import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.decision import DecisionGateway, VerificationResult
from daily_win_api.ai.decision.policy import Verdict, combine_verification
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
from daily_win_api.domains.daily_wins.feedback import feedback_exists_for_win
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
) -> DemoDailyWinRead:
    resolved = child or get_demo_child(session)
    if resolved is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)

    locked = session.scalars(
        select(Child).where(Child.id == resolved.id).with_for_update()
    ).first()
    if locked is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)
    resolved = locked

    try:
        prep = prepare_daily_win_generation(session, resolved)
    except ContextUnavailableError:
        raise DailyWinGenerationError(
            "demo_unavailable", 404, CLIENT_UNAVAILABLE
        ) from None

    latest = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == resolved.id,
            DailyWin.household_id == resolved.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(1)
    ).first()
    if latest is not None and not feedback_exists_for_win(session, latest.id):
        raise DailyWinGenerationError(
            "feedback_required", 409, CLIENT_FEEDBACK_REQUIRED
        )

    plan_skill = session.scalar(
        select(Skill).where(Skill.code == prep.plan.primary_skill_code)
    )
    if plan_skill is None:
        raise DailyWinGenerationError("unknown_skill", 422, CLIENT_GENERATION_FAILED)

    plan_row = InstructionPlanRecord(
        id=uuid4(),
        household_id=resolved.household_id,
        child_id=resolved.id,
        primary_skill_id=plan_skill.id,
        policy_version=prep.plan.policy_version,
        instruction_mode=prep.plan.instruction_mode.value,
        scaffold_level=prep.plan.scaffold_level.value,
        reason_codes=list(prep.plan.selection_reason_codes),
        plan=plan_as_dict(prep.plan),
    )
    session.add(plan_row)
    session.flush()
    prep.manifest.instruction_plan_id = plan_row.id

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
        context_manifest=prep.manifest.model_dump(mode="json"),
        started_at=now,
    )
    session.add(run)
    session.flush()

    allowed_codes = set(prep.context.allowed_skill_codes)
    last_reject: Exception | None = None
    result: DailyWinGenerationResult | None = None
    for _attempt in range(MAX_GENERATION_ATTEMPTS):
        try:
            result = gateway.generate_daily_win(prep.context)
        except ModelGatewayConfigurationError as exc:
            code = sanitize_error_code(exc.code)
            _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
            session.flush()
            raise DailyWinGenerationError(code, 503, CLIENT_GENERATION_FAILED) from None
        except ModelGatewaySchemaError as exc:
            logger.error("Daily Win schema failure (%s)", type(exc).__name__)
            code = sanitize_error_code(exc.code)
            _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
            session.flush()
            raise DailyWinGenerationError(code, 502, CLIENT_GENERATION_FAILED) from None
        except ModelGatewayError as exc:
            logger.error("Daily Win provider failure (%s)", type(exc).__name__)
            code = sanitize_error_code(exc.code)
            _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
            session.flush()
            raise DailyWinGenerationError(code, 502, CLIENT_GENERATION_FAILED) from None
        except Exception as exc:
            logger.error("Daily Win generation failed (%s)", type(exc).__name__)
            _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code="provider_error")
            session.flush()
            raise DailyWinGenerationError(
                "provider_error", 502, CLIENT_GENERATION_FAILED
            ) from None

        _apply_result_metadata(run, result)
        try:
            _validate_skill_contract(result.draft, allowed_codes, prep.plan)
            validate_renderer_contract(result.draft, prep.plan)
            validate_daily_win_safety(result.draft)
            review_generated_daily_win(result.draft)
            if decision_gateway is not None:
                verification = decision_gateway.evaluate_activity(
                    prep.plan, result.draft, tuple(prep.context.recent_themes)
                )
                _persist_decision_run(
                    session,
                    resolved=resolved,
                    plan_row=plan_row,
                    verification=verification,
                )
                verdict = combine_verification(verification)
                if verdict is Verdict.FAIL:
                    raise SkillContractError("verification_failed")
                if verdict is Verdict.UNCERTAIN:
                    raise SkillContractError("verification_uncertain")
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
            )
            session.flush()
            raise DailyWinGenerationError(code, 422, CLIENT_GENERATION_FAILED) from None
        code = sanitize_error_code(last_reject.code)
        _complete_run(
            run,
            status=AI_RUN_STATUS_REJECTED,
            error_code=code,
            result=result,
        )
        session.flush()
        raise DailyWinGenerationError(code, 422, CLIENT_GENERATION_FAILED) from None

    assert result is not None
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
    _complete_run(run, status=AI_RUN_STATUS_SUCCEEDED, result=result)
    session.flush()
    return to_demo_daily_win_read(session, daily_win, plan_skill, resolved.nickname)


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
) -> None:
    if result is not None:
        _apply_result_metadata(run, result)
    run.status = status
    run.error_code = error_code
    run.completed_at = datetime.now(UTC)
