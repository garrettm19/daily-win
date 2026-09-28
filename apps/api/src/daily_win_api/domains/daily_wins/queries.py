from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.core.demo import get_demo_child
from daily_win_api.domains.children.models import Child
from daily_win_api.domains.daily_wins.models import DailyWin, DailyWinFeedback
from daily_win_api.domains.daily_wins.schemas import (
    DAILY_WIN_STATUS_READY,
    BonusChallengeRead,
    CoachCueRead,
    DemoDailyWinRead,
    DiscoveryDomainRead,
    DiscoveryWeekRead,
    LearningEngineDebugRead,
    ParentAssessmentRead,
    ResultSnapshotRead,
    SmartReflectionRead,
)
from daily_win_api.domains.learning.coach_language import GUIDE_ONBOARDING
from daily_win_api.domains.learning.coach_protocol import protocol_from_dict
from daily_win_api.domains.learning.discovery import (
    DISCOVERY_BODY,
    DISCOVERY_HEADLINE,
    discovery_domain_status,
    discovery_is_active,
)
from daily_win_api.domains.learning.models import InstructionPlanRecord, Skill
from daily_win_api.domains.learning.presentation import (
    asks_about_setback,
    difficulty_debug_label,
    domain_label,
    evidence_debug_label,
    is_academic_probe,
    mode_label,
    placement_debug_label,
    probe_asks_for_counts,
    reason_labels,
    scaffold_label,
    selected_goal_label,
    shortened_task,
    success_looks_like,
    what_changed_today,
    what_to_check,
)
from daily_win_api.domains.learning.smart_reflection import smart_reflection_fields
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
    payload = (
        plan_row.plan
        if plan_row is not None and isinstance(plan_row.plan, dict)
        else {}
    )
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
                f"{domain_label(primary_skill.domain)} — {primary_skill.display_name}"
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
            selected_goal=selected_goal_label(
                primary_skill.code, primary_skill.display_name
            ),
            expected_entry=(
                str(payload["placement_entry_label"])
                if payload.get("placement_entry_label")
                else None
            ),
            evidence=evidence_debug_label(
                str(academic_band) if academic_band else None, reason_list
            ),
            placement=placement_debug_label(reason_list, plan_row.instruction_mode),
            placement_why=(
                str(payload["placement_why"]) if payload.get("placement_why") else None
            ),
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
    protocol = protocol_from_dict(
        payload["coach_protocol"]
        if isinstance(payload.get("coach_protocol"), dict)
        else None
    )
    coach_card = list(protocol.coach_card) if protocol else []
    cues = (
        [CoachCueRead(label=cue.label, text=cue.text) for cue in protocol.cues]
        if protocol
        else []
    )
    bonus = None
    raw_bonus = payload.get("bonus_challenge")
    if isinstance(raw_bonus, dict) and raw_bonus.get("code"):
        bonus = BonusChallengeRead(
            code=str(raw_bonus.get("code") or ""),
            category=str(raw_bonus.get("category") or ""),
            title=str(raw_bonus.get("title") or ""),
            minutes=int(raw_bonus.get("minutes") or 5),
            prompt=str(raw_bonus.get("prompt") or ""),
            safety=str(raw_bonus.get("safety") or ""),
            personal_best=bool(raw_bonus.get("personal_best")),
            optional=bool(raw_bonus.get("optional", True)),
            counts_as_mastery=bool(raw_bonus.get("counts_as_mastery", False)),
        )
    smart = None
    if plan_row is not None:
        fields = smart_reflection_fields(
            instruction_mode=plan_row.instruction_mode,
            skill_code=primary_skill.code,
            asks_about_setback=setback,
            teach_the_coach=bool(payload.get("teach_the_coach")),
        )
        smart = SmartReflectionRead(
            questions=list(fields["questions"]),
            notice_chips=list(fields["notice_chips"]),
            strategy_options=list(fields["strategy_options"]),
            self_correction_options=list(fields["self_correction_options"]),
            effort_options=list(fields["effort_options"]),
            bonus_engagement_options=list(fields["bonus_engagement_options"]),
        )
    discovery = _discovery_read(session, daily_win, payload)
    onboarding = None if _has_prior_wins(session, daily_win) else list(GUIDE_ONBOARDING)
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
        coach_card=coach_card,
        coach_cues=cues,
        wait_guidance=protocol.wait_guidance if protocol else None,
        bonus_challenge=bonus,
        smart_reflection=smart,
        discovery=discovery,
        guide_onboarding=onboarding,
        teach_the_coach=bool(payload.get("teach_the_coach")),
        protocol_version=protocol.protocol_version if protocol else None,
        one_thing_to_improve=protocol.one_thing_to_improve if protocol else None,
        result_snapshot=_result_snapshot(session, daily_win.id),
    )


def _discovery_read(
    session: Session, daily_win: DailyWin, payload: dict[str, object]
) -> DiscoveryWeekRead | None:
    from daily_win_api.domains.children.models import Child
    from daily_win_api.domains.learning.models import ChildGoal

    child = session.get(Child, daily_win.child_id)
    if child is None:
        return None
    goals = session.execute(
        select(ChildGoal, Skill)
        .join(Skill, Skill.id == ChildGoal.skill_id)
        .where(
            ChildGoal.child_id == child.id,
            ChildGoal.household_id == child.household_id,
            ChildGoal.active.is_(True),
        )
    ).all()
    goal_codes = tuple(skill.code for _goal, skill in goals)
    sampled: list[str] = []
    prior = session.execute(
        select(DailyWin, Skill)
        .join(Skill, Skill.id == DailyWin.primary_skill_id)
        .where(
            DailyWin.child_id == daily_win.child_id,
            DailyWin.household_id == daily_win.household_id,
            DailyWin.status == DAILY_WIN_STATUS_READY,
        )
    ).all()
    for _win, skill in prior:
        if is_academic_code(skill.code):
            sampled.append(skill.code.split(".", 1)[0].title())
    active = bool(payload.get("discovery_cycle")) or discovery_is_active(
        goal_codes, {}
    )
    if not active and not sampled:
        return None
    domains = discovery_domain_status(goal_codes, tuple(sampled))
    if not domains:
        return None
    return DiscoveryWeekRead(
        active=active or any(item["status"] == "still_to_explore" for item in domains),
        headline=DISCOVERY_HEADLINE,
        body=DISCOVERY_BODY,
        domains=[DiscoveryDomainRead(**item) for item in domains],
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


def _result_snapshot(session: Session, daily_win_id: UUID) -> ResultSnapshotRead | None:
    feedback = session.scalar(
        select(DailyWinFeedback).where(DailyWinFeedback.daily_win_id == daily_win_id)
    )
    if feedback is None:
        return None
    return ResultSnapshotRead(
        difficulty=feedback.difficulty,
        academic_result=feedback.academic_result,
        setback_response=feedback.setback_response,
        completion=feedback.completion,
        engagement=feedback.engagement,
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
