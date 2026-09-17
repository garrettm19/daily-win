from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from daily_win_api.db.session import SessionLocal


@pytest.fixture
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
