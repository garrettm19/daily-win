from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from daily_win_api.db.session import engine
from daily_win_api.dev.reset import reset_demo_derived_data
from daily_win_api.dev.seed import seed_development_data


@pytest.fixture
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def demo_db(db_session: Session) -> Session:
    seed_development_data(db_session)
    db_session.flush()
    reset_demo_derived_data(db_session)
    return db_session
