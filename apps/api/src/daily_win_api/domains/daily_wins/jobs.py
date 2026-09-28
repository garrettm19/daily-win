"""Process-level next-Win job runner. FastAPI stays in the API layer."""

from __future__ import annotations

import logging
from uuid import UUID

from daily_win_api.ai.exceptions import ModelGatewayConfigurationError
from daily_win_api.ai.gateway import build_model_gateway
from daily_win_api.db.session import SessionLocal
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.preparation import (
    TRIGGER_FIRST_PROFILE_SETUP,
    TRIGGER_REFLECTION,
    prepare_next_win,
)
from daily_win_api.domains.daily_wins.schemas import DailyWinGenerationError

logger = logging.getLogger(__name__)

# Tests disable this so TestClient background tasks do not touch SessionLocal.
BACKGROUND_PREGENERATE_ENABLED = True


def schedule_prepare_after_reflection(child_id: UUID, add_task) -> None:
    """add_task is FastAPI BackgroundTasks.add_task or any callable."""
    schedule_prepare_next_win(child_id, add_task, trigger=TRIGGER_REFLECTION)


def schedule_prepare_after_profile_setup(child_id: UUID, add_task) -> None:
    """Start first-Win Terra work after committed profile setup."""
    schedule_prepare_next_win(
        child_id, add_task, trigger=TRIGGER_FIRST_PROFILE_SETUP
    )


def schedule_prepare_next_win(child_id: UUID, add_task, *, trigger: str) -> None:
    if not BACKGROUND_PREGENERATE_ENABLED:
        return
    add_task(run_prepare_next_win_job, child_id, trigger)


def run_prepare_next_win_job(
    child_id: UUID, trigger: str = TRIGGER_REFLECTION
) -> None:
    if not BACKGROUND_PREGENERATE_ENABLED:
        return
    session = SessionLocal()
    try:
        child = session.get(Child, child_id)
        if child is None:
            return
        try:
            gateway = build_model_gateway()
        except ModelGatewayConfigurationError:
            logger.error("Next Win preparation skipped (configuration_error)")
            return
        prepare_next_win(
            session,
            gateway,
            child,
            trigger=trigger,
            commit_started=True,
        )
        session.commit()
    except DailyWinGenerationError:
        session.commit()
    except Exception:
        logger.error("Next Win preparation failed (%s)", "Exception")
        session.rollback()
    finally:
        session.close()
