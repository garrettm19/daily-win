from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from daily_win_api.db.session import get_db
from daily_win_api.domains.children.queries import (
    DemoChildProfileUnavailableError,
    load_demo_child_profile,
)
from daily_win_api.domains.children.schemas import DemoChildProfileRead

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
