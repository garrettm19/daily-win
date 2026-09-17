from uuid import uuid4

from sqlalchemy.orm import Session

from daily_win_api.domains.learning.models import LearningEvent
from daily_win_api.domains.learning.schemas import LearningEventCreate


def append_learning_event(session: Session, data: LearningEventCreate) -> LearningEvent:
    event = LearningEvent(
        id=uuid4(),
        household_id=data.household_id,
        child_id=data.child_id,
        skill_id=data.skill_id,
        evidence_kind=data.evidence_kind.value,
        source=data.source.value,
        event_type=data.event_type,
        occurred_at=data.occurred_at,
        payload=data.payload,
        schema_version=data.schema_version,
        confidence=data.confidence,
        supersedes_event_id=data.supersedes_event_id,
        daily_win_id=data.daily_win_id,
        daily_win_feedback_id=data.daily_win_feedback_id,
    )
    session.add(event)
    session.flush()
    return event
