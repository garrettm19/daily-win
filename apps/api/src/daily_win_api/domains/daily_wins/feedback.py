from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.insight import parent_insight
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.queries import academic_probe_for_win
from daily_win_api.domains.daily_wins.schemas import (
    CLIENT_UNAVAILABLE,
    DAILY_WIN_STATUS_READY,
    DailyWinFeedbackCreate,
    DailyWinGenerationError,
    DemoFeedbackRead,
    LearnedItem,
    ParentInsight,
    ParentLearnerStateSummary,
)
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    EvidenceKind,
    EvidenceSource,
)
from daily_win_api.domains.learning.events import append_learning_event
from daily_win_api.domains.learning.models import (
    InstructionPlanRecord,
    LearnerSkillState,
    Skill,
)
from daily_win_api.domains.learning.observations import (
    OBSERVATION_BONUS_ENGAGEMENT,
    OBSERVATION_EFFORT,
    OBSERVATION_NON_TARGET,
    OBSERVATION_NOTICE,
    OBSERVATION_SELF_CORRECTION,
    OBSERVATION_STRATEGY,
    observation_payload,
)
from daily_win_api.domains.learning.presentation import (
    academic_next_copy,
    academic_observation,
    domain_label,
    probe_asks_for_counts,
)
from daily_win_api.domains.learning.projector import rebuild_child_learner_states
from daily_win_api.domains.learning.schemas import LearningEventCreate
from daily_win_api.domains.learning.signals import (
    EVENT_TYPE_DAILY_WIN_FEEDBACK,
    EVENT_TYPE_SKILL_OBSERVATION,
    OBSERVATION_TYPE_SETBACK,
    PERSISTENCE_SKILL_CODE,
)
from daily_win_api.domains.learning.taxonomy import is_academic_code


class FeedbackUnavailableError(Exception):
    """Demo Daily Win is missing or not owned by the demo child."""


class FeedbackAlreadySubmittedError(Exception):
    """V0.1 allows one feedback submission per Daily Win."""


class FeedbackRejectedError(Exception):
    """Structured academic result was not valid for this Daily Win."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def submit_demo_feedback(
    session: Session,
    daily_win_id: UUID,
    data: DailyWinFeedbackCreate,
    child: Child | None = None,
) -> DemoFeedbackRead:
    resolved = child or get_demo_child(session)
    if resolved is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)

    daily_win = session.scalar(
        select(DailyWin).where(
            DailyWin.id == daily_win_id,
            DailyWin.child_id == resolved.id,
            DailyWin.household_id == resolved.household_id,
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

    primary_skill = session.get(Skill, daily_win.primary_skill_id)
    probe = academic_probe_for_win(session, daily_win, primary_skill)
    academic_result, correct_count, attempted_count = _validated_academic(
        data, probe=probe
    )

    now = datetime.now(UTC)
    feedback = DailyWinFeedback(
        id=uuid4(),
        household_id=resolved.household_id,
        child_id=resolved.id,
        daily_win_id=daily_win.id,
        difficulty=data.difficulty.value,
        engagement=data.engagement.value,
        completion=data.completion.value,
        setback_response=data.setback_response.value,
        what_helped=_optional_text(data.what_helped),
        additional_note=_optional_text(data.additional_note),
        academic_result=academic_result.value if academic_result else None,
        correct_count=correct_count,
        attempted_count=attempted_count,
        submitted_at=now,
    )
    session.add(feedback)
    session.flush()

    append_learning_event(
        session,
        LearningEventCreate(
            household_id=resolved.household_id,
            child_id=resolved.id,
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

    append_learning_event(
        session,
        LearningEventCreate(
            household_id=resolved.household_id,
            child_id=resolved.id,
            skill_id=persistence_skill.id,
            evidence_kind=EvidenceKind.OBSERVATION,
            source=EvidenceSource.PARENT,
            event_type=EVENT_TYPE_SKILL_OBSERVATION,
            occurred_at=now,
            payload={
                "observation_type": OBSERVATION_TYPE_SETBACK,
                "signal": feedback.setback_response,
                "reporting_kind": "parent_reported",
                "daily_win_id": str(daily_win.id),
            },
            daily_win_id=daily_win.id,
            daily_win_feedback_id=feedback.id,
        ),
    )

    if academic_result is not None and primary_skill is not None:
        measurement_payload: dict[str, object] = {
            "result": academic_result.value,
            "session_key": str(daily_win.id),
            "source": "parent_reported_measurement",
            "reporting_kind": "parent_reported_measurement",
        }
        if correct_count is not None:
            measurement_payload["correct_count"] = correct_count
        if attempted_count is not None:
            measurement_payload["attempted_count"] = attempted_count
        append_learning_event(
            session,
            LearningEventCreate(
                household_id=resolved.household_id,
                child_id=resolved.id,
                skill_id=primary_skill.id,
                evidence_kind=EvidenceKind.MEASUREMENT,
                source=EvidenceSource.PARENT,
                event_type=EVENT_TYPE_SKILL_ASSESSMENT,
                occurred_at=now,
                payload=measurement_payload,
                daily_win_id=daily_win.id,
                daily_win_feedback_id=feedback.id,
            ),
        )

    _append_optional_observations(
        session,
        resolved=resolved,
        daily_win=daily_win,
        feedback=feedback,
        data=data,
        now=now,
        primary_skill=primary_skill,
    )

    rebuild_child_learner_states(
        session,
        household_id=resolved.household_id,
        child_id=resolved.id,
    )
    state = session.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.household_id == resolved.household_id,
            LearnerSkillState.child_id == resolved.id,
            LearnerSkillState.skill_id == persistence_skill.id,
        )
    )
    if state is None:
        raise DailyWinGenerationError("demo_unavailable", 404, CLIENT_UNAVAILABLE)
    insight = parent_insight(resolved.nickname, feedback.setback_response)
    state_payload = state.state if isinstance(state.state, dict) else {}
    academic_copy, next_copy, _first = _academic_insight(
        session,
        resolved=resolved,
        primary_skill=primary_skill,
        academic_result=academic_result,
    )
    learned: list[LearnedItem] = []
    if academic_copy and primary_skill is not None:
        learned.append(
            LearnedItem(area=domain_label(primary_skill.domain), summary=academic_copy)
        )
    learned.append(LearnedItem(area="Persistence", summary=insight["observation"]))
    what_next = next_copy or insight["next_adjustment"]
    return DemoFeedbackRead(
        feedback_id=feedback.id,
        insight=ParentInsight(
            observation=insight["observation"],
            next_adjustment=what_next,
        ),
        learner_state=ParentLearnerStateSummary(
            skill_code=PERSISTENCE_SKILL_CODE,
            latest_signal=str(state_payload.get("latest_signal")),
            direction=str(state_payload.get("direction")),
            evidence_count=state.evidence_count,
        ),
        academic_observation=academic_copy,
        growth_observation=insight["observation"],
        what_we_learned=learned,
        what_changes_next=what_next,
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


def _append_optional_observations(
    session: Session,
    *,
    resolved: Child,
    daily_win: DailyWin,
    feedback: DailyWinFeedback,
    data: DailyWinFeedbackCreate,
    now: datetime,
    primary_skill: Skill | None,
) -> None:
    pairs: list[tuple[str, str, dict[str, object] | None]] = []
    if data.self_correction:
        pairs.append(
            (
                OBSERVATION_SELF_CORRECTION,
                data.self_correction,
                {"not_first_attempt_correct": True},
            )
        )
    if data.strategy_observed:
        pairs.append((OBSERVATION_STRATEGY, data.strategy_observed, None))
    if data.performance_effort:
        pairs.append((OBSERVATION_EFFORT, data.performance_effort, None))
    if data.bonus_engagement:
        extra: dict[str, object] = {"counts_as_mastery": False}
        category = _bonus_category_for_win(session, daily_win)
        if category:
            extra["category"] = category
        pairs.append(
            (
                OBSERVATION_BONUS_ENGAGEMENT,
                data.bonus_engagement,
                extra,
            )
        )
    if data.non_target_error:
        pairs.append(
            (
                OBSERVATION_NON_TARGET,
                data.non_target_error,
                {"does_not_create_mastery": True},
            )
        )
    for observation_type, value, extra in pairs:
        append_learning_event(
            session,
            LearningEventCreate(
                household_id=resolved.household_id,
                child_id=resolved.id,
                skill_id=primary_skill.id if primary_skill is not None else None,
                evidence_kind=EvidenceKind.OBSERVATION,
                source=EvidenceSource.PARENT,
                event_type=EVENT_TYPE_SKILL_OBSERVATION,
                occurred_at=now,
                payload=observation_payload(observation_type, value, extra=extra),
                daily_win_id=daily_win.id,
                daily_win_feedback_id=feedback.id,
            ),
        )
    if data.notice_chips:
        append_learning_event(
            session,
            LearningEventCreate(
                household_id=resolved.household_id,
                child_id=resolved.id,
                skill_id=None,
                evidence_kind=EvidenceKind.OBSERVATION,
                source=EvidenceSource.PARENT,
                event_type=EVENT_TYPE_SKILL_OBSERVATION,
                occurred_at=now,
                payload={
                    "observation_type": OBSERVATION_NOTICE,
                    "chips": list(data.notice_chips),
                    "reporting_kind": "parent_reported",
                    "epistemic_kind": "OBSERVATION",
                    "free_text_is_not_truth": True,
                },
                daily_win_id=daily_win.id,
                daily_win_feedback_id=feedback.id,
            ),
        )


def _validated_academic(
    data: DailyWinFeedbackCreate, *, probe: dict[str, object] | None
) -> tuple[AcademicResult | None, int | None, int | None]:
    if data.academic_result is None:
        if data.correct_count is not None or data.attempted_count is not None:
            raise FeedbackRejectedError("invalid_academic_counts")
        return None, None, None
    if probe is None:
        raise FeedbackRejectedError("academic_result_not_applicable")
    if not probe_asks_for_counts(probe):
        return data.academic_result, None, None
    return data.academic_result, data.correct_count, data.attempted_count


def _academic_insight(
    session: Session,
    *,
    resolved: Child,
    primary_skill: Skill | None,
    academic_result: AcademicResult | None,
) -> tuple[str | None, str | None, bool]:
    if (
        academic_result is None
        or primary_skill is None
        or not is_academic_code(primary_skill.code)
    ):
        return None, None, False
    state = session.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.household_id == resolved.household_id,
            LearnerSkillState.child_id == resolved.id,
            LearnerSkillState.skill_id == primary_skill.id,
        )
    )
    payload = state.state if state is not None and isinstance(state.state, dict) else {}
    sessions = int(payload.get("distinct_session_count") or 0)
    first = sessions <= 1
    try:
        band = AcademicBand(str(payload.get("band") or AcademicBand.EMERGING.value))
    except ValueError:
        band = AcademicBand.EMERGING
    needs = bool(payload.get("needs_remediation"))
    return (
        academic_observation(
            resolved.nickname,
            academic_result,
            first_evidence=first,
            skill_display_name=primary_skill.display_name,
        ),
        academic_next_copy(academic_result, needs_remediation=needs, band=band),
        first,
    )


def _bonus_category_for_win(session: Session, daily_win: DailyWin) -> str | None:
    if daily_win.instruction_plan_id is None:
        return None
    plan_row = session.get(InstructionPlanRecord, daily_win.instruction_plan_id)
    if plan_row is None or not isinstance(plan_row.plan, dict):
        return None
    bonus = plan_row.plan.get("bonus_challenge")
    if not isinstance(bonus, dict):
        return None
    category = bonus.get("category")
    return str(category) if category else None


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
