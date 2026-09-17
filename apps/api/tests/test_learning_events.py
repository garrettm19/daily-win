from datetime import UTC, datetime

from daily_win_api.core.demo import DEMO_CHILD_ID, DEMO_HOUSEHOLD_ID
from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.models import LearningEvent
from daily_win_api.domains.learning.schemas import LearningEventCreate


def test_learning_events_preserve_evidence_kind_and_source(db_session) -> None:
    seed_development_data(db_session)
    occurred_at = datetime.now(UTC)

    cases = (
        (EvidenceKind.FACT, EvidenceSource.PARENT, "parent_reported_grade"),
        (EvidenceKind.MEASUREMENT, EvidenceSource.ASSESSMENT, "activity_score"),
        (EvidenceKind.OBSERVATION, EvidenceSource.PARENT, "parent_observation"),
        (EvidenceKind.INFERENCE, EvidenceSource.AI, "derived_inference"),
    )

    created_ids = []
    for kind, source, event_type in cases:
        event = append_learning_event(
            db_session,
            LearningEventCreate(
                household_id=DEMO_HOUSEHOLD_ID,
                child_id=DEMO_CHILD_ID,
                evidence_kind=kind,
                source=source,
                event_type=event_type,
                occurred_at=occurred_at,
                payload={"synthetic": True},
            ),
        )
        created_ids.append((event.id, kind, source))

    for event_id, kind, source in created_ids:
        loaded = db_session.get(LearningEvent, event_id)
        assert loaded is not None
        assert loaded.evidence_kind == kind
        assert loaded.source == source
        assert loaded.household_id == DEMO_HOUSEHOLD_ID
        assert loaded.child_id == DEMO_CHILD_ID
