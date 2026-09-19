import json
from pathlib import Path

from daily_win_api.ai.exceptions import ModelGatewaySchemaError
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.ai.providers.openai import OpenAIModelGateway
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.eval.bakeoff import (
    LUNA,
    TERRA,
    arm_assignment,
    assert_review_is_blind,
    privacy_issues,
    run_terra_luna_bakeoff,
)
from daily_win_api.eval.bakeoff_cases import load_bakeoff_cases
from daily_win_api.eval.runner import build_parser


class _RetryOnceGateway:
    def __init__(self, model: str) -> None:
        self.model = model
        self.calls = 0
        self.contexts: list = []
        self._inner = FakeModelGateway(model=model)

    def generate_daily_win(self, context):
        self.calls += 1
        self.contexts.append(context)
        if self.calls == 1:
            raise ModelGatewaySchemaError("schema_validation_failed")
        return self._inner.generate_daily_win(context)


def test_bakeoff_cases_are_synthetic_and_cover_eight_intents() -> None:
    cases = load_bakeoff_cases()
    assert len(cases) == 8
    assert [item.coverage for item in cases] == [
        "age 5 math introduction",
        "age 6 reading/phonics",
        "age 7 writing organization",
        "age 8 diagnostic math",
        "age 9 reading comprehension",
        "remediation case",
        "review/retained case",
        "growth overlay + academic target",
    ]
    ages = {item.context.parent_reported_baseline.age_years for item in cases}
    assert {5, 6, 7, 8, 9} <= ages
    for case in cases:
        dumped = case.context.model_dump_json()
        assert privacy_issues(dumped) == []
        assert "child_id" not in dumped
        assert "household_id" not in dumped


def test_bakeoff_cases_match_current_planner() -> None:
    cases = {item.id: item for item in load_bakeoff_cases()}
    expected = {
        "case_1_age5_math_intro": ("math.number_sense.counting", "introduce"),
        "case_2_age6_phonics": ("reading.phonics.blend_cvc", "introduce"),
        "case_3_age7_writing_org": (
            "writing.sentences.complete_sentence",
            "introduce",
        ),
        "case_4_age8_diagnostic_math": ("math.addition.within_10", "diagnostic"),
        "case_5_age9_comprehension": (
            "reading.comprehension.simple_inference",
            "diagnostic",
        ),
        "case_6_remediation": ("math.addition.within_10", "remediation"),
        "case_7_review_retained": ("math.addition.within_10", "review"),
        "case_8_growth_overlay": ("math.addition.within_10", "diagnostic"),
    }
    for case_id, (skill, mode) in expected.items():
        case = cases[case_id]
        assert case.plan.primary_skill_code == skill
        assert case.plan.instruction_mode.value == mode
    assert cases["case_8_growth_overlay"].plan.growth_target_code == (
        "growth.persistence"
    )


def test_fake_bakeoff_freezes_identical_context(tmp_path) -> None:
    terra = FakeModelGateway(model=TERRA)
    luna = FakeModelGateway(model=LUNA)
    paths = run_terra_luna_bakeoff(
        live=False,
        output_dir=tmp_path,
        gateways={TERRA: terra, LUNA: luna},
    )
    assert len(terra.calls) == len(luna.calls) == 8
    for left, right in zip(terra.calls, luna.calls, strict=True):
        assert left.model_dump_json() == right.model_dump_json()
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["live"] is False
    assert payload["production_default_unchanged"] is True
    assert payload["routing_implemented"] is False
    assert payload["baseline_model"] == DEFAULT_OPENAI_MODEL
    assert payload["calls_succeeded"] == 16
    assert "not canonical learner memory" in payload["note"]
    review = paths["review"].read_text(encoding="utf-8")
    assert_review_is_blind(review)
    assert "OUTPUT A" in review
    assert "OUTPUT B" in review
    assert "Would use with my child" in review
    assert "Authoritative InstructionPlan" in review
    reveal = json.loads(paths["reveal"].read_text(encoding="utf-8"))
    first = reveal["assignment"]["case_1"]
    assert first["A"] in {TERRA, LUNA}
    assert first["A"] != first["B"]


def test_ab_assignment_is_deterministic() -> None:
    first = arm_assignment("case_1_age5_math_intro")
    second = arm_assignment("case_1_age5_math_intro")
    assert first == second
    assert {first.a_model, first.b_model} == {TERRA, LUNA}


def test_schema_retry_is_recorded_once(tmp_path) -> None:
    flaky = _RetryOnceGateway(TERRA)
    luna = FakeModelGateway(model=LUNA)
    paths = run_terra_luna_bakeoff(
        live=False,
        output_dir=tmp_path,
        gateways={TERRA: flaky, LUNA: luna},
    )
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    first = payload["cases"][0]["outputs"][TERRA]
    assert first["retried"] is True
    assert first["retry_reason"] == "schema_validation_failed"
    assert first["attempts"] == 2
    assert payload["calls_retried"] == 1
    assert flaky.calls == 9
    assert flaky.contexts[0].model_dump_json() == flaky.contexts[1].model_dump_json()


def test_cli_exposes_terra_luna_compare() -> None:
    args = build_parser().parse_args(["--compare", "terra-luna"])
    assert args.compare == "terra-luna"
    live = build_parser().parse_args(["--compare", "terra-luna", "--live"])
    assert live.live is True


def test_production_default_remains_terra() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    assert DEFAULT_OPENAI_MODEL == "gpt-5.6-terra"
    assert "OPENAI_MODEL=gpt-5.6-terra" in example.read_text(encoding="utf-8")


def test_openai_gateway_keeps_store_false() -> None:
    captured: dict[str, object] = {}

    class _Client:
        class responses:
            @staticmethod
            def parse(**kwargs):
                captured.update(kwargs)

                class _Usage:
                    input_tokens = 1
                    output_tokens = 1
                    total_tokens = 2

                class _Response:
                    output_parsed = FakeModelGateway().draft
                    usage = _Usage()
                    id = "resp_test"

                return _Response()

    gateway = OpenAIModelGateway(api_key="test", model=TERRA, client=_Client())
    gateway.generate_daily_win(load_bakeoff_cases()[0].context)
    assert captured["store"] is False
    assert captured["model"] == TERRA
