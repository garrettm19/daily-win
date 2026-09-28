from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.api.errors import generation_error_payload
from daily_win_api.domains.daily_wins.renderer_contract import (
    AGE_RESPECTFUL_FOUNDATION,
    DIAGNOSTIC_PROBE_BEFORE_TEACHING,
    FRESH_ASSESSMENT_ITEM,
    HARD_RULE_CODES,
    ONE_CANONICAL_ASSESSMENT,
    PRIMARY_SKILL_TIME_MAJORITY,
    REVIEW_PRACTICE_THEN_CHECK,
    THREE_CONCRETE_CUES,
    contracts_for_plan,
    renderer_contract_hard_failures,
    renderer_contract_soft_flags,
    validate_renderer_contract,
)
from daily_win_api.domains.daily_wins.schemas import (
    CLIENT_GENERATION_FAILED,
    RendererContractError,
)
from daily_win_api.eval.renderer_contract_cases import labelled_renderer_contract_cases
from daily_win_api.eval.suites import run_quality_suite


def test_labelled_blind_review_fixtures_match_expected_rules() -> None:
    cases = labelled_renderer_contract_cases()
    assert len(cases) == 18
    labels = {case.label for case in cases}
    assert labels == {"good", "bad"}
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        hard = renderer_contract_hard_failures(case.draft, case.plan)
        soft = renderer_contract_soft_flags(case.draft, case.plan)
        if case.expect_hard is None:
            assert hard == ()
        else:
            assert case.expect_hard in hard
        if case.expect_soft is not None:
            assert case.expect_soft in soft
        else:
            assert soft == ()


def test_validate_raises_renderer_contract_error() -> None:
    bad = next(
        case
        for case in labelled_renderer_contract_cases()
        if case.id == "case1_bad_vague_three_step"
    )
    try:
        validate_renderer_contract(bad.draft, bad.plan)
    except RendererContractError as exc:
        assert exc.code == "renderer_contract_failed"
        assert exc.rule == THREE_CONCRETE_CUES
    else:
        raise AssertionError("expected RendererContractError")


def test_good_three_step_and_diagnostic_order_pass() -> None:
    by_id = {case.id: case for case in labelled_renderer_contract_cases()}
    validate_renderer_contract(
        by_id["case1_good_three_step_cues"].draft,
        by_id["case1_good_three_step_cues"].plan,
    )
    validate_renderer_contract(
        by_id["case3_good_diagnostic_first"].draft,
        by_id["case3_good_diagnostic_first"].plan,
    )
    validate_renderer_contract(
        by_id["case2_good_fresh_item"].draft,
        by_id["case2_good_fresh_item"].plan,
    )


def test_fresh_item_not_forced_on_qualitative_construct() -> None:
    draft = valid_daily_win_draft(
        primary_skill_code="reading.comprehension.simple_inference"
    )
    case = next(
        item
        for item in labelled_renderer_contract_cases()
        if item.id == "case5_good_one_canonical"
    )
    plan = case.plan
    assert FRESH_ASSESSMENT_ITEM not in contracts_for_plan(plan)
    assert FRESH_ASSESSMENT_ITEM not in renderer_contract_hard_failures(draft, plan)


def test_hard_rule_codes_are_stable() -> None:
    assert HARD_RULE_CODES == {
        AGE_RESPECTFUL_FOUNDATION,
        THREE_CONCRETE_CUES,
        DIAGNOSTIC_PROBE_BEFORE_TEACHING,
        ONE_CANONICAL_ASSESSMENT,
        PRIMARY_SKILL_TIME_MAJORITY,
        REVIEW_PRACTICE_THEN_CHECK,
        FRESH_ASSESSMENT_ITEM,
    }


def test_dev_reason_allows_renderer_contract_rule() -> None:
    payload = generation_error_payload(
        CLIENT_GENERATION_FAILED,
        "renderer_contract_failed",
        include_error_code=True,
        dev_reason=THREE_CONCRETE_CUES,
    )
    assert payload["error_code"] == "renderer_contract_failed"
    assert payload["dev_reason"] == THREE_CONCRETE_CUES


def test_quality_suite_includes_renderer_contract_fixtures() -> None:
    result = run_quality_suite()
    assert result.failed == 0, result.errors
    assert result.total >= 16
