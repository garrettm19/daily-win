from daily_win_api.domains.learning.coach_language import (
    ANTI_PATTERNS,
    GUIDE_ONBOARDING,
)
from daily_win_api.domains.learning.coach_protocol import (
    LEVEL_LIGHT_CUE,
    LEVEL_MODEL,
    LEVEL_REDUCE,
    LEVEL_STRATEGY,
    LEVEL_WAIT,
    build_coach_protocol,
    contains_banned_coaching,
    protocol_from_dict,
)
from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel
from daily_win_api.domains.learning.frustration import (
    DISENGAGED,
    MILD_ENGAGED,
    classify_frustration,
    frustration_guidance,
)
from daily_win_api.domains.learning.planner import plan_instruction, plan_instruction_v3
from daily_win_api.eval.builders import planner_input


def _protocol(
    mode: InstructionMode,
    *,
    age: int = 9,
    skill: str = "math.addition.within_20",
):
    return build_coach_protocol(
        instruction_mode=mode,
        scaffold=ScaffoldLevel.MEDIUM,
        age_years=age,
        skill_code=skill,
        academic_band=None,
        growth_target_code="growth.persistence",
    )


def test_diagnostic_support_ceiling() -> None:
    protocol = _protocol(InstructionMode.DIAGNOSTIC)
    assert protocol.prompt_ceiling == LEVEL_WAIT
    assert protocol.allowed_prompt_levels == (LEVEL_WAIT,)
    assert "Do not teach" in protocol.assessment_boundary
    assert any("independently" in item.lower() for item in protocol.coach_card)
    assert protocol.teach_the_coach is False


def test_introduce_allows_model() -> None:
    protocol = _protocol(InstructionMode.INTRODUCE)
    assert protocol.prompt_ceiling == LEVEL_MODEL
    assert LEVEL_MODEL in protocol.allowed_prompt_levels
    assert LEVEL_WAIT in protocol.allowed_prompt_levels


def test_practice_prompt_ladder() -> None:
    protocol = _protocol(InstructionMode.PRACTICE)
    assert protocol.prompt_ceiling == LEVEL_STRATEGY
    assert LEVEL_REDUCE not in protocol.allowed_prompt_levels
    wait = protocol.initial_wait_behavior.lower()
    assert "wait" in wait or "moment" in wait


def test_remediation_support() -> None:
    protocol = _protocol(InstructionMode.REMEDIATION)
    assert protocol.prompt_ceiling == LEVEL_REDUCE
    assert "reduce" in protocol.struggle_policy.lower()


def test_review_independence() -> None:
    protocol = _protocol(InstructionMode.REVIEW)
    assert protocol.prompt_ceiling == LEVEL_LIGHT_CUE
    assert protocol.teach_the_coach is True


def test_frustration_and_self_correction() -> None:
    protocol = _protocol(InstructionMode.PRACTICE)
    assert "distress" in protocol.frustration_response.lower()
    assert "first-attempt" in protocol.self_correction_response.lower()
    mild = classify_frustration(
        notice_chips=("got frustrated",),
        setback_response="continued_after_prompt",
    )
    assert mild == MILD_ENGAGED
    assert "strategy" in " ".join(frustration_guidance(mild)).lower()
    stopped = classify_frustration(setback_response="stopped_or_avoided")
    assert stopped == DISENGAGED
    assert any("dignity" in item.lower() for item in frustration_guidance(stopped))


def test_age_respectful_and_writing_one_thing() -> None:
    young = _protocol(InstructionMode.PRACTICE, age=6, skill="writing.spelling.cvc")
    older = _protocol(
        InstructionMode.PRACTICE,
        age=9,
        skill="writing.spelling.endings_suffixes",
    )
    assert young.one_thing_to_improve
    assert older.teach_the_coach is True
    assert young.teach_the_coach is False
    assert len(GUIDE_ONBOARDING) == 6
    assert "praising intelligence" in ANTI_PATTERNS


def test_protocol_persists_on_v4_not_v3() -> None:
    data = planner_input(age_years=9, grade="4", goals=(("math.addition", 1),))
    plan = plan_instruction(data)
    assert plan.coach_protocol is not None
    assert plan.bonus_challenge is not None
    restored = protocol_from_dict(plan.coach_protocol)
    assert restored is not None
    assert restored.prompt_ceiling == LEVEL_WAIT
    v3 = plan_instruction_v3(data)
    assert v3.coach_protocol is None
    assert v3.bonus_challenge is None


def test_banned_empty_praise() -> None:
    assert contains_banned_coaching("Great job! You are so smart")
    assert not contains_banned_coaching("You tried a different strategy.")
