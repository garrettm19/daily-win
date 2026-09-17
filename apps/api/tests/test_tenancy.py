from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.households.models import Household
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.schemas import LearningEventCreate


def test_cross_household_child_ownership_is_rejected(db_session) -> None:
    household_a = Household(id=uuid4(), display_name="Household A")
    household_b = Household(id=uuid4(), display_name="Household B")
    db_session.add_all([household_a, household_b])
    db_session.flush()

    child_a = Child(id=uuid4(), household_id=household_a.id, nickname="SyntheticA")
    db_session.add(child_a)
    db_session.flush()

    mismatched_baseline = ChildBaseline(
        id=uuid4(),
        household_id=household_b.id,
        child_id=child_a.id,
        recorded_at=datetime.now(UTC),
        age_years=7,
        grade="1",
        interests=[],
        strengths=[],
        current_difficulties=[],
        motivators=[],
        preferred_activity_minutes=20,
        schema_version=1,
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(mismatched_baseline)
            db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            append_learning_event(
                db_session,
                LearningEventCreate(
                    household_id=household_b.id,
                    child_id=child_a.id,
                    evidence_kind=EvidenceKind.OBSERVATION,
                    source=EvidenceSource.PARENT,
                    event_type="parent_observation",
                    occurred_at=datetime.now(UTC),
                    payload={"synthetic": True},
                ),
            )
            db_session.flush()
