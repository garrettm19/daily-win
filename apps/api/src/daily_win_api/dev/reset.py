from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import DEMO_CHILD_ID, DEMO_HOUSEHOLD_ID
from daily_win_api.db.session import SessionLocal
from daily_win_api.dev.models import DemoSession
from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.learning.models import (
    ChildGoal,
    DecisionRun,
    InstructionPlanRecord,
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
)


def reset_demo_derived_data(
    session: Session,
    *,
    child_id: UUID = DEMO_CHILD_ID,
    household_id: UUID = DEMO_HOUSEHOLD_ID,
) -> None:
    """Remove derived artifacts for one synthetic tenant.

    Preserves that tenant's household, child, baseline, goals, and the skill
    taxonomy. Does not touch other households.
    """
    state_ids = select(LearnerSkillState.id).where(
        LearnerSkillState.child_id == child_id,
        LearnerSkillState.household_id == household_id,
    )
    session.execute(
        delete(LearnerSkillStateEvidence).where(
            LearnerSkillStateEvidence.learner_skill_state_id.in_(state_ids)
        )
    )
    session.execute(
        delete(DailyWinFeedback).where(
            DailyWinFeedback.child_id == child_id,
            DailyWinFeedback.household_id == household_id,
        )
    )
    session.execute(
        delete(LearningEvent).where(
            LearningEvent.child_id == child_id,
            LearningEvent.household_id == household_id,
        )
    )
    session.execute(
        delete(DecisionRun).where(
            DecisionRun.child_id == child_id,
            DecisionRun.household_id == household_id,
        )
    )
    session.execute(
        delete(DailyWin).where(
            DailyWin.child_id == child_id,
            DailyWin.household_id == household_id,
        )
    )
    session.execute(
        delete(InstructionPlanRecord).where(
            InstructionPlanRecord.child_id == child_id,
            InstructionPlanRecord.household_id == household_id,
        )
    )
    session.execute(
        delete(AiRun).where(
            AiRun.child_id == child_id,
            AiRun.household_id == household_id,
        )
    )
    session.execute(
        delete(LearnerSkillState).where(
            LearnerSkillState.child_id == child_id,
            LearnerSkillState.household_id == household_id,
        )
    )
    session.flush()


def reset_demo_activity_history(
    session: Session, *, child_id: UUID, household_id: UUID
) -> None:
    """Clear Wins/evidence/state for a configured child. Profile stays."""
    reset_demo_derived_data(session, child_id=child_id, household_id=household_id)


def restart_demo_session(session: Session, row: DemoSession) -> None:
    """Remove this session's synthetic child and return it to first-run."""
    if row.child_id is not None:
        reset_demo_derived_data(
            session, child_id=row.child_id, household_id=row.household_id
        )
        session.execute(
            delete(ChildGoal).where(
                ChildGoal.child_id == row.child_id,
                ChildGoal.household_id == row.household_id,
            )
        )
        session.execute(
            delete(ChildBaseline).where(
                ChildBaseline.child_id == row.child_id,
                ChildBaseline.household_id == row.household_id,
            )
        )
        child_id = row.child_id
        row.child_id = None
        row.profile_source = None
        session.flush()
        child = session.get(Child, child_id)
        if child is not None:
            session.delete(child)
        session.flush()
        return
    row.child_id = None
    row.profile_source = None
    session.flush()


def reset_all_demo_tenants(session: Session) -> None:
    """Maintainer wipe of every demo session plus the legacy shared Hayes."""
    seed_development_data(session)
    reset_demo_derived_data(session)
    rows = list(session.scalars(select(DemoSession)))
    for row in rows:
        restart_demo_session(session, row)
    seed_development_data(session)
    session.flush()


def main() -> None:
    session = SessionLocal()
    try:
        reset_all_demo_tenants(session)
        session.commit()
        print("Demo reset complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
