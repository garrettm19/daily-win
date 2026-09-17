from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.daily_wins.insight import parent_insight
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    CLIENT_UNAVAILABLE,
    DAILY_WIN_STATUS_READY,
    DailyWinFeedbackCreate,
    DailyWinGenerationError,
    DemoFeedbackRead,
    ParentInsight,
    ParentLearnerStateSummary,
)
from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.models import Skill
from daily_win_api.domains.learning.projector import project_persistence_state
from daily_win_api.domains.learning.schemas import LearningEventCreate
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_DAILY_WIN_FEEDBACK,
    EVENT_TYPE_SKILL_OBSERVATION,
    OBSERVATION_TYPE_SETBACK,
    PERSISTENCE_SKILL_CODE,
)


class FeedbackUnavailableError(Exception):
    """Demo Daily Win is missing or not owned by the demo child."""


class FeedbackAlreadySubmittedError(Exception):
    """V0.1 allows one feedback submission per Daily Win."""


def submit_demo_feedback(
    session: Session, daily_win_id: UUID, data: DailyWinFeedbackCreate
) -> DemoFeedbackRead:
    child = get_demo_child(session)
    if child is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)

    daily_win = session.scalar(
        select(DailyWin).where(
            DailyWin.id == daily_win_id,
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
    )
    if daily_win is None:
        raise FeedbackUnavailableError

    existing = session.scalar(
        select(DailyWinFeedback).where(DailyWinFeedback.daily_win_id == daily_win.id)
    )
    if existing is not None:
        raise FeedbackAlreadySubmittedError

    now = datetime.now(UTC)
    feedback = DailyWinFeedback(
        id=uuid4(),
        household_id=child.household_id,
        child_id=child.id,
        daily_win_id=daily_win.id,
        difficulty=data.difficulty.value,
        engagement=data.engagement.value,
        completion=data.completion.value,
        setback_response=data.setback_response.value,
        what_helped=_optional_text(data.what_helped),
        additional_note=_optional_text(data.additional_note),
        submitted_at=now,
    )
    session.add(feedback)
    session.flush()

    append_learning_event(
        session,
        LearningEventCreate(
            household_id=child.household_id,
            child_id=child.id,
            skill_id=None,
            evidence_kind=EvidenceKind.OBSERVATION,
            source=EvidenceSource.PARENT,
            event_type=EVENT_TYPE_DAILY_WIN_FEEDBACK,
            occurred_at=now,
            payload={
                "difficulty": feedback.difficulty,
                "engagement": feedback.engagement,
                "completion": feedback.completion,
                "reporting_kind": "parent_reported",
            },
            daily_win_id=daily_win.id,
            daily_win_feedback_id=feedback.id,
        ),
    )

    persistence_skill = session.scalar(
        select(Skill).where(Skill.code == PERSISTENCE_SKILL_CODE)
    )
    if persistence_skill is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)

    observation_payload: dict[str, object] = {
        "observation_type": OBSERVATION_TYPE_SETBACK,
        "signal": feedback.setback_response,
        "reporting_kind": "parent_reported",
        "daily_win_id": str(daily_win.id),
    }
    if feedback.what_helped:
        observation_payload["what_helped"] = feedback.what_helped

    append_learning_event(
        session,
        LearningEventCreate(
            household_id=child.household_id,
            child_id=child.id,
            skill_id=daily_win.primary_skill_id,
            evidence_kind=EvidenceKind.OBSERVATION,
            source=EvidenceSource.PARENT,
            event_type=EVENT_TYPE_SKILL_OBSERVATION,
            occurred_at=now,
            payload=observation_payload,
            daily_win_id=daily_win.id,
            daily_win_feedback_id=feedback.id,
        ),
    )

    state = project_persistence_state(
        session,
        household_id=child.household_id,
        child_id=child.id,
        skill=persistence_skill,
    )
    insight = parent_insight(child.nickname, feedback.setback_response)
    state_payload = state.state if isinstance(state.state, dict) else {}
    return DemoFeedbackRead(
        feedback_id=feedback.id,
        insight=ParentInsight(
            observation=insight["observation"],
            next_adjustment=insight["next_adjustment"],
        ),
        learner_state=ParentLearnerStateSummary(
            skill_code=PERSISTENCE_SKILL_CODE,
            latest_signal=str(state_payload.get("latest_signal")),
            direction=str(state_payload.get("direction")),
            evidence_count=state.evidence_count,
        ),
    )


def feedback_exists_for_win(session: Session, daily_win_id: UUID) -> bool:
    return (
        session.scalar(
            select(DailyWinFeedback.id).where(
                DailyWinFeedback.daily_win_id == daily_win_id
            )
        )
        is not None
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
