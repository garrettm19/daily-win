from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_READY,
    DemoDailyWinRead,
    LearningEngineDebugRead,
    ParentAssessmentRead,
)
from daily_win_api.domains.learning.models import InstructionPlanRecord, Skill
from daily_win_api.domains.learning.presentation import (
    asks_about_setback,
    difficulty_debug_label,
    domain_label,
    is_academic_probe,
    mode_label,
    probe_asks_for_counts,
    reason_labels,
    scaffold_label,
    shortened_task,
    success_looks_like,
    what_changed_today,
    what_to_check,
)
from daily_win_api.domains.learning.support import REFLECTION_CAPTION
from daily_win_api.domains.learning.taxonomy import is_academic_code


def get_demo_daily_win(
    session: Session, daily_win_id: UUID, child: Child
) -> DemoDailyWinRead | None:
    daily_win = session.scalar(
        select(DailyWin).where(
            DailyWin.id == daily_win_id,
            DailyWin.child_id == child.id,
            DailyWin.household_id == child.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
    )
    if daily_win is None:
        return None
    skill = session.get(Skill, daily_win.primary_skill_id)
    if skill is None:
        return None
    return to_demo_daily_win_read(session, daily_win, skill, child.nickname)


def get_latest_demo_daily_win(
    session: Session, child: Child | None = None
) -> DemoDailyWinRead | None:
    resolved = child or get_demo_child(session)
    if resolved is None:
        return None
    daily_win = session.scalars(
        select(DailyWin)
        .where(
            DailyWin.child_id == resolved.id,
            DailyWin.household_id == resolved.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
        .order_by(DailyWin.created_at.desc(), DailyWin.id.desc())
        .limit(1)
    ).first()
    if daily_win is None:
        return None
    skill = session.get(Skill, daily_win.primary_skill_id)
    if skill is None:
        return None
    return to_demo_daily_win_read(session, daily_win, skill, resolved.nickname)


def to_demo_daily_win_read(
    session: Session, daily_win: DailyWin, primary_skill: Skill, child_nickname: str
) -> DemoDailyWinRead:
    plan_row = _plan_row(session, daily_win)
    probe = _probe_from_plan(plan_row)
    academic = is_academic_probe(probe, primary_skill.code)
    assessment = None
    learning_engine = None
    changed = None
    setback = True
    if plan_row is not None:
        payload = plan_row.plan if isinstance(plan_row.plan, dict) else {}
        growth = payload.get("growth_target_code")
        growth_code = growth if isinstance(growth, str) else None
        setback = asks_about_setback(growth_code, has_plan=True)
        if academic and probe is not None:
            task = str(probe.get("observable_task") or primary_skill.display_name)
            expected = str(probe.get("expected_outcome") or task)
            assessment = ParentAssessmentRead(
                what_to_check=what_to_check(child_nickname, task),
                success_looks_like=success_looks_like(expected),
                prompt_label=shortened_task(task),
                asks_for_counts=probe_asks_for_counts(probe),
                support_caption=REFLECTION_CAPTION,
            )
        reasons = payload.get("selection_reason_codes") or plan_row.reason_codes
        reason_list = (
            [str(item) for item in reasons] if isinstance(reasons, list) else []
        )
        academic_band = payload.get("academic_band")
        learning_engine = LearningEngineDebugRead(
            target=(
                f"{domain_label(primary_skill.domain)} — "
                f"{primary_skill.display_name}"
            ),
            mode=mode_label(plan_row.instruction_mode),
            difficulty=difficulty_debug_label(
                str(academic_band) if academic_band else None
            ),
            scaffold=scaffold_label(plan_row.scaffold_level),
            why=reason_labels(reason_list),
            assessment=shortened_task(
                str((probe or {}).get("observable_task") or primary_skill.display_name)
            ),
            policy=plan_row.policy_version,
        )
        changed = what_changed_today(
            has_prior_wins=_has_prior_wins(session, daily_win),
            skill_display_name=primary_skill.display_name,
            reason_codes=reason_list,
            instruction_mode=plan_row.instruction_mode,
            scaffold=plan_row.scaffold_level,
            growth_summary=(
                str(payload["growth_adaptation_summary"])
                if payload.get("growth_adaptation_summary")
                else None
            ),
        )
    return DemoDailyWinRead(
        id=daily_win.id,
        child_nickname=child_nickname,
        title=daily_win.title,
        objective=daily_win.objective,
        duration_minutes=daily_win.duration_minutes,
        primary_skill_code=primary_skill.code,
        primary_skill_display_name=primary_skill.display_name,
        content=DailyWinDraft.model_validate(daily_win.content),
        has_feedback=_feedback_exists(session, daily_win.id),
        created_at=daily_win.created_at,
        assessment=assessment,
        asks_about_setback=setback,
        what_changed_today=changed,
        learning_engine=learning_engine,
    )


def academic_probe_for_win(
    session: Session, daily_win: DailyWin, primary_skill: Skill | None
) -> dict[str, object] | None:
    if primary_skill is None or not is_academic_code(primary_skill.code):
        return None
    probe = _probe_from_plan(_plan_row(session, daily_win))
    if not is_academic_probe(probe, primary_skill.code):
        return None
    return probe


def _plan_row(session: Session, daily_win: DailyWin) -> InstructionPlanRecord | None:
    if daily_win.instruction_plan_id is None:
        return None
    return session.get(InstructionPlanRecord, daily_win.instruction_plan_id)


def _probe_from_plan(
    plan_row: InstructionPlanRecord | None,
) -> dict[str, object] | None:
    if plan_row is None or not isinstance(plan_row.plan, dict):
        return None
    probe = plan_row.plan.get("assessment_probe")
    return probe if isinstance(probe, dict) else None


def _feedback_exists(session: Session, daily_win_id: UUID) -> bool:
    return (
        session.scalar(
            select(DailyWinFeedback.id).where(
                DailyWinFeedback.daily_win_id == daily_win_id
            )
        )
        is not None
    )


def _has_prior_wins(session: Session, daily_win: DailyWin) -> bool:
    prior_id = session.scalar(
        select(DailyWin.id)
        .where(
            DailyWin.child_id == daily_win.child_id,
            DailyWin.household_id == daily_win.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
            DailyWin.created_at < daily_win.created_at,
        )
        .limit(1)
    )
    return prior_id is not None
