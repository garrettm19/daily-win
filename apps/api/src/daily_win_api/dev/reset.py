from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import DEMO_CHILD_ID, DEMO_HOUSEHOLD_ID
from daily_win_api.db.session import SessionLocal
from daily_win_api.dev.seed import seed_development_data
from daily_win_api.domains.daily_wins.models import AiRun, DailyWin, DailyWinFeedback
from daily_win_api.domains.learning.models import (
    LearnerSkillState,
    LearnerSkillStateEvidence,
    LearningEvent,
)


def reset_demo_derived_data(session: Session) -> None:
    """Remove demo-derived artifacts for the synthetic Hayes child only.

    Preserves the demo household, child, baseline, goals, and skill taxonomy.
    """
    state_ids = select(LearnerSkillState.id).where(
        LearnerSkillState.child_id == DEMO_CHILD_ID,
        LearnerSkillState.household_id == DEMO_HOUSEHOLD_ID,
    )
    session.execute(
        delete(LearnerSkillStateEvidence).where(
            LearnerSkillStateEvidence.learner_skill_state_id.in_(state_ids)
        )
    )
    session.execute(
        delete(DailyWinFeedback).where(
            DailyWinFeedback.child_id == DEMO_CHILD_ID,
            DailyWinFeedback.household_id == DEMO_HOUSEHOLD_ID,
        )
    )
    session.execute(
        delete(LearningEvent).where(
            LearningEvent.child_id == DEMO_CHILD_ID,
            LearningEvent.household_id == DEMO_HOUSEHOLD_ID,
        )
    )
    session.execute(
        delete(DailyWin).where(
            DailyWin.child_id == DEMO_CHILD_ID,
            DailyWin.household_id == DEMO_HOUSEHOLD_ID,
        )
    )
    session.execute(
        delete(AiRun).where(
            AiRun.child_id == DEMO_CHILD_ID,
            AiRun.household_id == DEMO_HOUSEHOLD_ID,
        )
    )
    session.execute(
        delete(LearnerSkillState).where(
            LearnerSkillState.child_id == DEMO_CHILD_ID,
            LearnerSkillState.household_id == DEMO_HOUSEHOLD_ID,
        )
    )
    session.flush()


def main() -> None:
    session = SessionLocal()
    try:
        seed_development_data(session)
        reset_demo_derived_data(session)
        seed_development_data(session)
        session.commit()
        print("Demo reset complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
