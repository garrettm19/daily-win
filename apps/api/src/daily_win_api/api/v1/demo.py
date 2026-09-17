import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from daily_win_api.ai.gateway import ModelGateway
from daily_win_api.api.deps import get_model_gateway
from daily_win_api.api.errors import SanitizedClientError
from daily_win_api.db.session import get_db
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.children.queries import (
    DemoChildProfileUnavailableError,
    load_demo_child_profile,
)
from daily_win_api.domains.children.schemas import DemoChildProfileRead
from daily_win_api.domains.daily_wins.feedback import (
    FeedbackAlreadySubmittedError,
    FeedbackUnavailableError,
    submit_demo_feedback,
)
from daily_win_api.domains.daily_wins.queries import get_latest_demo_daily_win
from daily_win_api.domains.daily_wins.schemas import (
    CLIENT_FEEDBACK_EXISTS,
    CLIENT_FEEDBACK_FAILED,
    CLIENT_FEEDBACK_NOT_FOUND,
    CLIENT_GENERATION_FAILED,
    CLIENT_RESET_FAILED,
    DailyWinFeedbackCreate,
    DailyWinGenerationError,
    DemoDailyWinRead,
    DemoFeedbackRead,
    DemoResetRead,
)
from daily_win_api.domains.daily_wins.service import generate_demo_daily_win

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.get("/child-profile", response_model=DemoChildProfileRead)
def read_demo_child_profile(
    db: Annotated[Session, Depends(get_db)],
) -> DemoChildProfileRead:
    """Development/demo only. Not production authorization."""
    try:
        return load_demo_child_profile(db)
    except DemoChildProfileUnavailableError:
        raise HTTPException(
            status_code=404,
            detail="Demo child profile is not available.",
        ) from None


@router.post("/daily-wins/generate", response_model=DemoDailyWinRead)
def create_demo_daily_win(
    db: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> DemoDailyWinRead:
    """Development/demo only. Not production authorization."""
    try:
        result = generate_demo_daily_win(db, gateway)
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
        ) from None


@router.get("/daily-wins/latest", response_model=DemoDailyWinRead)
def read_latest_demo_daily_win(
    db: Annotated[Session, Depends(get_db)],
) -> DemoDailyWinRead:
    """Development/demo only. Not production authorization."""
    result = get_latest_demo_daily_win(db)
    if result is None:
        raise HTTPException(status_code=404, detail="No Daily Win is available yet.")
    return result


@router.post(
    "/daily-wins/{daily_win_id}/feedback",
    response_model=DemoFeedbackRead,
)
def create_demo_daily_win_feedback(
    daily_win_id: UUID,
    payload: DailyWinFeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DemoFeedbackRead:
    """Development/demo only. Not production authorization."""
    try:
        result = submit_demo_feedback(db, daily_win_id, payload)
        db.commit()
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
    except DailyWinGenerationError as exc:
        db.rollback()
        raise SanitizedClientError(
            status_code=exc.http_status,
            detail=CLIENT_FEEDBACK_FAILED,
            error_code=exc.code,
        ) from None
    except Exception:
        db.rollback()
        raise SanitizedClientError(
            status_code=500,
            detail=CLIENT_FEEDBACK_FAILED,
            error_code="provider_error",
        ) from None


@router.post("/reset", response_model=DemoResetRead)
def reset_demo_state(
    db: Annotated[Session, Depends(get_db)],
) -> DemoResetRead:
    """Development/demo only. Restores the synthetic Hayes starting condition."""
    try:
        seed_development_data(db)
        reset_demo_derived_data(db)
        seed_development_data(db)
        db.commit()
        return DemoResetRead()
    except Exception as exc:
        logger.error("Demo reset failed (%s)", type(exc).__name__)
        db.rollback()
        raise SanitizedClientError(
            status_code=500,
            detail=CLIENT_RESET_FAILED,
            error_code="provider_error",
        ) from None
