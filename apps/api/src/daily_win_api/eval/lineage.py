"""Canonical evidence lineage checks. Not learner truth."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.models import (
    InstructionPlanRecord,
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
)
from daily_win_api.domains.learning.signals import EVENT_TYPE_DAILY_WIN_FEEDBACK


def lineage_errors(session: Session, child: Child) -> list[str]:
    errors: list[str] = []
    wins = session.scalars(
        select(DailyWin).where(
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
        )
    ).all()
    for win in wins:
        if win.instruction_plan_id is None:
            errors.append(f"win {win.title} missing instruction_plan")
            continue
        plan = session.get(InstructionPlanRecord, win.instruction_plan_id)
        if plan is None:
            errors.append(f"win {win.title} orphaned instruction_plan")
        elif plan.child_id != child.id or plan.household_id != child.household_id:
            errors.append("instruction_plan household/child mismatch")
        feedback = session.scalar(
            select(DailyWinFeedback).where(DailyWinFeedback.daily_win_id == win.id)
        )
        if feedback is None:
            continue
        events = session.scalars(
            select(LearningEvent).where(LearningEvent.daily_win_id == win.id)
        ).all()
        types = {event.event_type for event in events}
        if EVENT_TYPE_DAILY_WIN_FEEDBACK not in types:
            errors.append(f"feedback for {win.title} missing daily_win_feedback event")
        assessments = [
            event for event in events if event.event_type == EVENT_TYPE_SKILL_ASSESSMENT
        ]
        if len(assessments) > 1:
            errors.append(f"duplicate measurement for {win.title}")
        for event in assessments:
            if event.skill_id != win.primary_skill_id:
                errors.append(f"measurement skill mismatch for {win.title}")
            if event.daily_win_feedback_id != feedback.id:
                errors.append(f"measurement not linked to feedback for {win.title}")
    state_ids = {
        row.id
        for row in session.scalars(
            select(LearnerSkillState).where(
                LearnerSkillState.child_id == child.id,
                LearnerSkillState.household_id == child.household_id,
            )
        )
    }
    event_ids = {
        row.id
        for row in session.scalars(
            select(LearningEvent).where(
                LearningEvent.child_id == child.id,
                LearningEvent.household_id == child.household_id,
            )
        )
    }
    links = (
        session.scalars(
            select(LearnerSkillStateEvidence).where(
                LearnerSkillStateEvidence.learner_skill_state_id.in_(state_ids)
            )
        ).all()
        if state_ids
        else []
    )
    for link in links:
        if (
            link.learner_skill_state_id in state_ids
            and link.learning_event_id not in event_ids
        ):
            errors.append("state evidence points at missing event")
    return errors
