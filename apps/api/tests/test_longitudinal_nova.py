from datetime import UTC, datetime, timedelta
from uuid import uuid4

from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    AcademicEvidence,
    AcademicStateSnapshot,
    project_academic_band,
)
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    InstructionMode,
    ScaffoldLevel,
)
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    PlannerInput,
    PlannerSkillState,
    plan_instruction,
)

NOW = datetime(2026, 3, 1, tzinfo=UTC)


def _item(result: AcademicResult, day: int, session: str) -> AcademicEvidence:
    return AcademicEvidence(
        event_id=uuid4(),
        occurred_at=NOW + timedelta(days=day),
        result=result,
        session_key=session,
    )


def _retained(code: str) -> PlannerSkillState:
    practiced = NOW - timedelta(days=1)
    return PlannerSkillState(
        code,
        AcademicStateSnapshot(
            band=AcademicBand.RETAINED,
            algorithm_version=ACADEMIC_PROJECTOR_V1,
            usable_evidence_count=4,
            distinct_session_count=4,
            last_practiced_at=practiced,
            last_independent_success_at=practiced,
            evidence_ids=(),
            summary="retained",
            needs_remediation=False,
        ),
    )


def _plan_for(snapshot, now: datetime):
    return plan_instruction(
        PlannerInput(
            nickname="Nova",
            age_years=8,
            grade="3",
            interests=("space",),
            motivators=("stories",),
            preferred_duration_minutes=20,
            goals=(
                GoalPriority("math.addition", 1),
                GoalPriority("growth.persistence", 2),
            ),
            states={
                "math.number_sense.counting": _retained("math.number_sense.counting"),
                "math.addition.within_10": PlannerSkillState(
                    "math.addition.within_10", snapshot
                ),
            },
            recent_skill_codes=("math.addition.within_10",),
            recent_themes=("Rocket tally",),
            now=now,
        )
    )


def test_nova_academic_state_evolves_conservatively() -> None:
    s1 = [_item(AcademicResult.INCORRECT, 0, "1")]
    s2 = s1 + [_item(AcademicResult.CORRECT_AFTER_LIGHT_PROMPT, 2, "2")]
    s3 = s2 + [_item(AcademicResult.CORRECT_INDEPENDENTLY, 4, "3")]
    s4 = s3 + [_item(AcademicResult.CORRECT_INDEPENDENTLY, 12, "4")]

    b1 = project_academic_band(s1, now=NOW)
    b2 = project_academic_band(s2, now=NOW + timedelta(days=2))
    b3 = project_academic_band(s3, now=NOW + timedelta(days=4))
    b4 = project_academic_band(s4, now=NOW + timedelta(days=12))

    assert b1.band is AcademicBand.EMERGING
    assert b2.band is AcademicBand.DEVELOPING
    assert b3.band is AcademicBand.DEVELOPING
    assert b4.band is AcademicBand.RETAINED
    assert b3.band is not AcademicBand.RETAINED
    assert b4.evidence_ids
    assert b4.distinct_session_count == 4

    p1 = _plan_for(b1, NOW)
    p2 = _plan_for(b2, NOW + timedelta(days=2))
    p3 = _plan_for(b3, NOW + timedelta(days=4))
    p4 = _plan_for(b4, NOW + timedelta(days=12))

    assert p1.scaffold_level is ScaffoldLevel.HIGH
    assert p2.scaffold_level is ScaffoldLevel.MEDIUM
    assert p3.scaffold_level is ScaffoldLevel.MEDIUM
    assert p1.primary_skill_code == "math.addition.within_10"
    assert p3.primary_skill_code == "math.addition.within_10"
    assert p4.primary_skill_code == "math.addition.within_20"
    assert p4.instruction_mode is InstructionMode.DIAGNOSTIC


def test_nova_regression_schedules_review() -> None:
    evidence = [
        _item(AcademicResult.CORRECT_INDEPENDENTLY, 0, "1"),
        _item(AcademicResult.INCORRECT, 8, "2"),
        _item(AcademicResult.INCORRECT, 9, "3"),
    ]
    snap = project_academic_band(evidence, now=NOW + timedelta(days=9))
    assert snap.band is AcademicBand.DEVELOPING
    plan = _plan_for(snap, NOW + timedelta(days=9))
    assert plan.instruction_mode is InstructionMode.REMEDIATION
    assert "regression_review" in plan.selection_reason_codes
    assert plan.scaffold_level is ScaffoldLevel.HIGH
