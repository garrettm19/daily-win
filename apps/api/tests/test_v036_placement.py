"""V0.3.6 age/grade-aware placement. Age is a prior; evidence is level."""

from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.domains.daily_wins.renderer_contract import (
    AGE_RESPECTFUL_FOUNDATION,
    contracts_for_plan,
    renderer_contract_hard_failures,
)
from daily_win_api.domains.learning.enums import AcademicBand, InstructionMode
from daily_win_api.domains.learning.placement import (
    PLACEMENT_POLICY_V1,
    decide_placement,
    is_unknown,
    observed_weak,
)
from daily_win_api.domains.learning.planner import (
    INSTRUCTION_POLICY_V4,
    plan_instruction,
)
from daily_win_api.eval.builders import planner_input, snapshot, state
from daily_win_api.eval.planner_cases import evaluate_planner_case, planner_golden_cases


def test_unknown_is_not_weakness() -> None:
    assert is_unknown(None) is True
    assert observed_weak(None) is False
    assert is_unknown(snapshot(AcademicBand.NOT_OBSERVED)) is True
    assert observed_weak(snapshot(AcademicBand.NOT_OBSERVED)) is False
    assert observed_weak(snapshot(AcademicBand.EMERGING)) is True


def test_age9_spelling_no_evidence_is_not_cvc() -> None:
    decision = decide_placement("writing.spelling", 9, {})
    assert decision.skill_code == "writing.spelling.multisyllabic_irregular"
    assert decision.sparse_evidence is True
    assert decision.policy_version == PLACEMENT_POLICY_V1
    plan = plan_instruction(
        planner_input(age_years=9, grade="4", goals=(("writing.spelling", 1),))
    )
    assert plan.primary_skill_code == "writing.spelling.multisyllabic_irregular"
    assert plan.instruction_mode is InstructionMode.DIAGNOSTIC
    assert plan.policy_version == INSTRUCTION_POLICY_V4
    assert "writing.spelling.cvc" != plan.primary_skill_code


def test_age9_addition_no_evidence_is_not_counting() -> None:
    plan = plan_instruction(
        planner_input(age_years=9, grade="4", goals=(("math.addition", 1),))
    )
    assert plan.primary_skill_code == "math.addition.word_problems"
    assert plan.instruction_mode is InstructionMode.DIAGNOSTIC


def test_age9_reading_no_evidence_is_not_letter_sounds() -> None:
    plan = plan_instruction(
        planner_input(age_years=9, grade="4", goals=(("reading.comprehension", 1),))
    )
    assert plan.primary_skill_code == "reading.comprehension.simple_inference"
    assert plan.primary_skill_code != "reading.phonics.letter_sounds"


def test_weak_diagnostic_steps_down_one_level() -> None:
    plan = plan_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=(("writing.spelling", 1),),
            states=(
                state(
                    "writing.spelling.multisyllabic_irregular",
                    AcademicBand.EMERGING,
                    sessions=1,
                ),
            ),
        )
    )
    assert plan.primary_skill_code == "writing.spelling.endings_suffixes"
    assert "placement_step_down" in plan.selection_reason_codes
    assert plan.primary_skill_code != "writing.spelling.cvc"


def test_age9_cvc_foundation_sets_age_respectful_contract() -> None:
    plan = plan_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=(("writing.spelling", 1),),
            states=(state("writing.spelling.cvc", AcademicBand.EMERGING, sessions=2),),
        )
    )
    assert plan.primary_skill_code == "writing.spelling.cvc"
    assert plan.presentation_constraint == AGE_RESPECTFUL_FOUNDATION
    assert AGE_RESPECTFUL_FOUNDATION in contracts_for_plan(plan)
    baby = valid_daily_win_draft(primary_skill_code="writing.spelling.cvc")
    learn, do, grow = baby.segments
    dirty = baby.model_copy(
        update={
            "segments": [
                learn.model_copy(
                    update={"steps": ["Sound it out like a baby word for little kids."]}
                ),
                do,
                grow,
            ]
        }
    )
    assert AGE_RESPECTFUL_FOUNDATION in renderer_contract_hard_failures(dirty, plan)
    clean = valid_daily_win_draft(primary_skill_code="writing.spelling.cvc")
    assert AGE_RESPECTFUL_FOUNDATION not in renderer_contract_hard_failures(clean, plan)


def test_placement_golden_cases_pass() -> None:
    cases = [case for case in planner_golden_cases() if case.id.startswith("place_")]
    assert len(cases) >= 12
    errors = [item for case in cases for item in evaluate_planner_case(case)]
    assert errors == []
