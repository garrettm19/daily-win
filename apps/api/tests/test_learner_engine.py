from datetime import UTC, datetime, timedelta
from uuid import uuid4

from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    AcademicEvidence,
    AcademicStateSnapshot,
    due_for_review,
    project_academic_band,
)
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    EvidenceKind,
    InstructionMode,
    ScaffoldLevel,
)
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    PlannerInput,
    PlannerSkillState,
    plan_instruction,
)
from daily_win_api.domains.learning.prerequisites import (
    has_cycle,
    prerequisites_for,
)
from daily_win_api.domains.learning.probes import probe_for_skill
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import (
    SKILL_DEFINITIONS,
    child_skills_for_parent,
    is_academic_code,
    is_growth_or_life_code,
)

NOW = datetime(2026, 9, 19, tzinfo=UTC)


def _evidence(
    result: AcademicResult, day: int, session: str, event_id=None
) -> AcademicEvidence:
    return AcademicEvidence(
        event_id=event_id or uuid4(),
        occurred_at=NOW + timedelta(days=day),
        result=result,
        session_key=session,
    )


def test_curriculum_hierarchy_and_codes() -> None:
    codes = {item["code"] for item in SKILL_DEFINITIONS}
    assert "math.addition.within_10" in codes
    assert "math.addition.within_20" in codes
    assert "math.addition.word_problems" in codes
    assert "writing.organization.sequence_events" in codes
    assert "writing.sentences.complete_sentence" in codes
    assert "reading.comprehension.recall_details" in codes
    children = child_skills_for_parent("math.addition")
    assert [item["code"] for item in children] == [
        "math.addition.within_10",
        "math.addition.within_20",
        "math.addition.word_problems",
    ]
    assert is_academic_code("math.addition.within_10")
    assert is_growth_or_life_code("growth.persistence")
    assert not is_academic_code("growth.persistence")


def test_prerequisites_have_no_cycles() -> None:
    assert has_cycle() is False
    assert prerequisites_for("math.addition.within_20") == ("math.addition.within_10",)
    assert prerequisites_for("math.addition.within_10") == (
        "math.number_sense.counting",
    )
    assert prerequisites_for("math.subtraction.within_10") == (
        "math.addition.within_10",
    )
    assert prerequisites_for("math.multiplication.equal_groups") == (
        "math.addition.within_10",
    )
    assert prerequisites_for("reading.fluency.smooth_oral") == (
        "reading.phonics.blend_cvc",
    )
    assert prerequisites_for("writing.spelling.high_frequency") == (
        "reading.phonics.blend_cvc",
    )
    assert prerequisites_for("writing.spelling.cvc") == ("reading.phonics.blend_cvc",)
    assert prerequisites_for("writing.spelling.patterns") == ("writing.spelling.cvc",)
    assert prerequisites_for("writing.spelling.endings_suffixes") == (
        "writing.spelling.patterns",
    )
    assert prerequisites_for("writing.spelling.multisyllabic_irregular") == (
        "writing.spelling.endings_suffixes",
    )
    assert prerequisites_for("math.fractions.halves_fourths") == ()


def test_standards_are_metadata_not_identity() -> None:
    mapped = {item["skill_code"] for item in SKILL_STANDARD_REFS}
    assert "math.addition.within_10" in mapped
    assert "growth.persistence" not in mapped
    assert all(item["source"] for item in SKILL_STANDARD_REFS)
    assert all(item["version"] for item in SKILL_STANDARD_REFS)


def test_probe_cannot_change_target() -> None:
    probe = probe_for_skill("math.addition.within_10")
    assert probe["target_skill_code"] == "math.addition.within_10"
    assert probe["success_criteria"]


def test_one_success_is_not_mastery() -> None:
    snap = project_academic_band(
        [_evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1")],
        now=NOW,
    )
    assert snap.band is AcademicBand.DEVELOPING
    assert snap.algorithm_version == ACADEMIC_PROJECTOR_V1


def test_support_level_impacts_state() -> None:
    helped = project_academic_band(
        [_evidence(AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP, 0, "s1")],
        now=NOW,
    )
    prompted = project_academic_band(
        [_evidence(AcademicResult.CORRECT_AFTER_LIGHT_PROMPT, 0, "s1")],
        now=NOW,
    )
    assert helped.band is AcademicBand.EMERGING
    assert prompted.band is AcademicBand.DEVELOPING


def test_retained_requires_spaced_independent_evidence() -> None:
    close = project_academic_band(
        [
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1"),
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 2, "s2"),
        ],
        now=NOW + timedelta(days=2),
    )
    spaced = project_academic_band(
        [
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1"),
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 8, "s2"),
        ],
        now=NOW + timedelta(days=8),
    )
    assert close.band is AcademicBand.DEMONSTRATED
    assert spaced.band is AcademicBand.RETAINED


def test_regression_moves_state_backward() -> None:
    snap = project_academic_band(
        [
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1"),
            _evidence(AcademicResult.INCORRECT, 3, "s2"),
            _evidence(AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP, 4, "s3"),
        ],
        now=NOW + timedelta(days=4),
    )
    assert snap.band is AcademicBand.DEVELOPING


def test_review_spacing_after_demonstrated() -> None:
    snap = project_academic_band(
        [
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1"),
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 1, "s2"),
        ],
        now=NOW + timedelta(days=1),
    )
    assert due_for_review(snap, now=NOW + timedelta(days=1)) is False
    assert due_for_review(snap, now=NOW + timedelta(days=16)) is True


def test_skipped_is_not_usable_measurement() -> None:
    snap = project_academic_band(
        [_evidence(AcademicResult.NOT_ATTEMPTED, 0, "s1")],
        now=NOW,
    )
    assert snap.band is AcademicBand.NOT_OBSERVED
    assert snap.usable_evidence_count == 0


def _planner(
    *,
    goals: tuple[GoalPriority, ...],
    states: dict[str, PlannerSkillState] | None = None,
    interests: tuple[str, ...] = ("soccer",),
    age: int = 7,
) -> PlannerInput:
    return PlannerInput(
        nickname="Nova",
        age_years=age,
        grade="2",
        interests=interests,
        motivators=("stories",),
        preferred_duration_minutes=20,
        goals=goals,
        states=states or {},
        recent_skill_codes=(),
        recent_themes=("Old Tower Win",),
        now=NOW,
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


def test_planner_is_deterministic_and_explains_why() -> None:
    first = plan_instruction(
        _planner(
            goals=(
                GoalPriority("writing.organization", 1),
                GoalPriority("growth.persistence", 2),
            )
        )
    )
    second = plan_instruction(
        _planner(
            goals=(
                GoalPriority("writing.organization", 1),
                GoalPriority("growth.persistence", 2),
            )
        )
    )
    assert first == second
    assert first.primary_skill_code == "writing.organization.sequence_events"
    assert "parent_priority" in first.selection_reason_codes
    assert first.policy_version == "instruction_policy_v4"
    assert first.assessment_probe["target_skill_code"] == first.primary_skill_code


def test_engagement_cannot_override_instructional_objective() -> None:
    counting = {"math.number_sense.counting": _retained("math.number_sense.counting")}
    soccer = plan_instruction(
        _planner(
            goals=(GoalPriority("math.addition", 1),),
            interests=("soccer", "Minecraft"),
            states=counting,
        )
    )
    space = plan_instruction(
        _planner(
            goals=(GoalPriority("math.addition", 1),),
            interests=("space",),
            states=counting,
        )
    )
    assert soccer.primary_skill_code == space.primary_skill_code
    assert soccer.primary_skill_code == "math.addition.within_20"
    assert soccer.engagement_theme_constraints[0] == "soccer"
    assert space.engagement_theme_constraints[0] == "space"


def test_planner_reviews_missing_prerequisite() -> None:
    plan = plan_instruction(
        _planner(
            goals=(GoalPriority("math.addition.within_20", 1),),
            states={
                "math.number_sense.counting": _retained("math.number_sense.counting"),
                "math.addition.within_10": PlannerSkillState(
                    "math.addition.within_10",
                    AcademicStateSnapshot(
                        band=AcademicBand.EMERGING,
                        algorithm_version=ACADEMIC_PROJECTOR_V1,
                        usable_evidence_count=1,
                        distinct_session_count=1,
                        last_practiced_at=NOW,
                        last_independent_success_at=None,
                        evidence_ids=(),
                        summary="weak",
                        needs_remediation=False,
                    ),
                ),
            },
        )
    )
    assert plan.primary_skill_code == "math.addition.within_10"
    assert "prerequisite_evidence_missing" in plan.selection_reason_codes


def test_older_learner_unobserved_skill_is_diagnostic() -> None:
    plan = plan_instruction(
        _planner(
            goals=(GoalPriority("math.addition", 1),),
            age=9,
        )
    )
    assert plan.primary_skill_code == "math.addition.word_problems"
    assert plan.instruction_mode is InstructionMode.DIAGNOSTIC
    assert "diagnostic_check" in plan.selection_reason_codes
    assert plan.academic_band == AcademicBand.NOT_OBSERVED.value
    assert "math.number_sense.counting" != plan.primary_skill_code


def test_planner_schedules_remediation_after_regression() -> None:
    snapshot = project_academic_band(
        [
            _evidence(AcademicResult.CORRECT_INDEPENDENTLY, 0, "s1"),
            _evidence(AcademicResult.INCORRECT, 2, "s2"),
            _evidence(AcademicResult.INCORRECT, 3, "s3"),
        ],
        now=NOW + timedelta(days=3),
    )
    plan = plan_instruction(
        _planner(
            goals=(GoalPriority("math.addition.within_10", 1),),
            states={
                "math.number_sense.counting": _retained("math.number_sense.counting"),
                "math.addition.within_10": PlannerSkillState(
                    "math.addition.within_10", snapshot
                ),
            },
        )
    )
    assert plan.instruction_mode is InstructionMode.REMEDIATION
    assert plan.scaffold_level is ScaffoldLevel.HIGH
    assert "regression_review" in plan.selection_reason_codes


def test_evidence_kinds_remain_distinct() -> None:
    assert EvidenceKind.FACT.value == "FACT"
    assert EvidenceKind.MEASUREMENT.value == "MEASUREMENT"
    assert EvidenceKind.OBSERVATION.value == "OBSERVATION"
    assert EvidenceKind.INFERENCE.value == "INFERENCE"
