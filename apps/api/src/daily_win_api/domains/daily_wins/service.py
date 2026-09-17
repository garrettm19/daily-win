import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.error_codes import sanitize_error_code
from daily_win_api.ai.exceptions import (
    ModelGatewayConfigurationError,
    ModelGatewayError,
    ModelGatewaySchemaError,
)
from daily_win_api.ai.gateway import ModelGateway
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import DailyWinDraft, DailyWinGenerationResult
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.context import build_daily_win_context
from daily_win_api.domains.daily_wins.feedback import feedback_exists_for_win
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin
from daily_win_api.domains.daily_wins.queries import to_demo_daily_win_read
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
    OPERATION_DAILY_WIN_GENERATE,
    OUTPUT_SCHEMA_VERSION,
    ContextUnavailableError,
    DailyWinGenerationError,
    DemoDailyWinRead,
    SafetyRejectedError,
    SkillContractError,
)
from daily_win_api.domains.learning.models import Skill

logger = logging.getLogger(__name__)


def generate_demo_daily_win(
    session: Session, gateway: ModelGateway
) -> DemoDailyWinRead:
    child = get_demo_child(session)
    if child is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)

    try:
        context, manifest = build_daily_win_context(session, child)
    except ContextUnavailableError:
        raise DailyWinGenerationError(
            "demo_unavailable", 404, CLIENT_UNAVAILABLE
        ) from None

    latest = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc())
        .limit(1)
    ).first()
    if latest is not None and not feedback_exists_for_win(session, latest.id):
        raise DailyWinGenerationError(
            "feedback_required", 409, CLIENT_FEEDBACK_REQUIRED
        )

    allowed_codes = set(context.allowed_skill_codes)
    primary_goal_code = context.primary_goal_skill_code
    now = datetime.now(UTC)
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
        context_manifest=manifest.model_dump(mode="json"),
        started_at=now,
    )
    session.add(run)
    session.flush()

    try:
        result = gateway.generate_daily_win(context)
    except ModelGatewayConfigurationError as exc:
        code = sanitize_error_code(exc.code)
        _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
        session.flush()
        raise DailyWinGenerationError(
            code, 503, CLIENT_GENERATION_FAILED
        ) from None
    except ModelGatewaySchemaError as exc:
        logger.error("Daily Win schema failure (%s)", type(exc).__name__)
        code = sanitize_error_code(exc.code)
        _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
        session.flush()
        raise DailyWinGenerationError(
            code, 502, CLIENT_GENERATION_FAILED
        ) from None
    except ModelGatewayError as exc:
        logger.error("Daily Win provider failure (%s)", type(exc).__name__)
        code = sanitize_error_code(exc.code)
        _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code=code)
        session.flush()
        raise DailyWinGenerationError(
            code, 502, CLIENT_GENERATION_FAILED
        ) from None
    except Exception as exc:
        logger.error("Daily Win generation failed (%s)", type(exc).__name__)
        _complete_run(run, status=AI_RUN_STATUS_FAILED, error_code="provider_error")
        session.flush()
        raise DailyWinGenerationError(
            "provider_error", 502, CLIENT_GENERATION_FAILED
        ) from None

    _apply_result_metadata(run, result)

    try:
        _validate_skill_contract(result.draft, allowed_codes, primary_goal_code)
        validate_daily_win_safety(result.draft)
    except SkillContractError as exc:
        code = sanitize_error_code(exc.code)
        _complete_run(
            run,
            status=AI_RUN_STATUS_REJECTED,
            error_code=code,
            result=result,
        )
        session.flush()
        raise DailyWinGenerationError(
            code, 422, CLIENT_GENERATION_FAILED
        ) from None
    except SafetyRejectedError as exc:
        code = sanitize_error_code(exc.code)
        _complete_run(
            run,
            status=AI_RUN_STATUS_REJECTED,
            error_code=code,
            result=result,
        )
        session.flush()
        raise DailyWinGenerationError(
            code, 422, CLIENT_GENERATION_FAILED
        ) from None

    primary_skill = session.scalar(
        select(Skill).where(Skill.code == result.draft.primary_skill_code)
    )
    if primary_skill is None:
        _complete_run(
            run,
            status=AI_RUN_STATUS_REJECTED,
            error_code="unknown_skill",
            result=result,
        )
        session.flush()
        raise DailyWinGenerationError(
            "unknown_skill", 422, CLIENT_GENERATION_FAILED
        ) from None

    draft = result.draft
    if not context.recent_daily_wins:
        draft = draft.model_copy(update={"adaptation_summary": None})

    daily_win = DailyWin(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        primary_skill_id=primary_skill.id,
        ai_run_id=run.id,
        title=draft.title,
        objective=draft.objective,
        duration_minutes=draft.duration_minutes,
        content=draft.model_dump(mode="json"),
        content_schema_version=CONTENT_SCHEMA_VERSION,
        status=DAILY_WIN_STATUS_READY,
    )
    session.add(daily_win)
    _complete_run(run, status=AI_RUN_STATUS_SUCCEEDED, result=result)
    session.flush()
    return to_demo_daily_win_read(session, daily_win, primary_skill, child.nickname)


def _validate_skill_contract(
    draft: DailyWinDraft, allowed_codes: set[str], primary_goal_code: str
) -> None:
    if draft.primary_skill_code not in allowed_codes:
        raise SkillContractError("unknown_skill")
    if draft.primary_skill_code != primary_goal_code:
        raise SkillContractError("primary_goal_mismatch")
    for code in draft.supporting_skill_codes:
        if code not in allowed_codes:
            raise SkillContractError("unknown_skill")


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

