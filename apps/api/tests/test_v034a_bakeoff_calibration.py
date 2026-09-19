import json
from pathlib import Path

import pytest

from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.domains.daily_wins.safety import (
    FIRE_OR_HEAT,
    validate_daily_win_safety,
)
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError
from daily_win_api.eval.attribution import (
    FailureOwner,
    original_safety_was_false_positive,
)
from daily_win_api.eval.bakeoff_rescore import rescore_terra_luna_artifact
from daily_win_api.eval.human_review import (
    parse_review_markdown,
    summarize_human_review,
)
from daily_win_api.eval.pricing import OPENAI_MODEL_PRICES, estimate_cost_parts
from daily_win_api.eval.runner import build_parser

ORIGINAL = (
    Path(__file__).resolve().parents[1]
    / "eval-results"
    / "20260919T211946Z-terra-luna.json"
)


def test_pricing_table_matches_openai_pages_2026_09_19() -> None:
    terra = OPENAI_MODEL_PRICES["gpt-5.6-terra"]
    luna = OPENAI_MODEL_PRICES["gpt-5.6-luna"]
    assert terra.input_usd_per_million == 2.00
    assert terra.output_usd_per_million == 12.00
    assert luna.input_usd_per_million == 0.20
    assert luna.output_usd_per_million == 1.20
    assert terra.last_verified_date.isoformat() == "2026-09-19"
    assert luna.last_verified_date.isoformat() == "2026-09-19"


def test_output_tokens_dominate_terra_cost_at_bakeoff_shape() -> None:
    parts = estimate_cost_parts("gpt-5.6-terra", 1998, 1281)
    assert parts is not None
    assert parts.output_usd > parts.input_usd
    assert parts.output_share > 0.7


def test_false_positive_attribution_for_corrected_safety() -> None:
    assert original_safety_was_false_positive(
        original_hard_failures=["unsafe_content"],
        current_safety_ok=True,
    )
    assert not original_safety_was_false_positive(
        original_hard_failures=["unsafe_content"],
        current_safety_ok=False,
    )
    assert FailureOwner.APPLICATION_VALIDATOR_FALSE_POSITIVE.value == (
        "APPLICATION_VALIDATOR_FALSE_POSITIVE"
    )


def test_luna_case5_clue_sentence_is_now_safe() -> None:
    draft = valid_daily_win_draft(
        extra_step="whether the inference matches the clues",
        safety_flags=[],
    )
    validate_daily_win_safety(draft)


def test_matchstick_instructions_still_fail() -> None:
    draft = valid_daily_win_draft(extra_step="Play with matches.", safety_flags=[])
    with pytest.raises(SafetyRejectedError) as caught:
        validate_daily_win_safety(draft)
    assert caught.value.rule == FIRE_OR_HEAT


def test_review_parser_aggregates_exploratory_scores() -> None:
    markdown = """
## Case 1 — age 5 math introduction

### Scores
Educational usefulness: A= 4 B= 5
Plan fidelity: A= 5 B= 5
Age appropriateness: A= 4 B= 4
Parent clarity: A= 4 B= 5
Engagement: A= 3 B= 4
Assessment quality: A= 4 B= 4
Coaching quality: A= 4 B= 5
Overall: A= 4 B= 5
Preference: B
Would use with my child: Both
Verdict A: PASS
Verdict B: PASS
Note: B a bit clearer.
"""
    parsed = parse_review_markdown(markdown)
    assert parsed[0]["complete"] is True
    summary = summarize_human_review(
        markdown,
        {
            "assignment": {
                "case_1": {
                    "A": "gpt-5.6-luna",
                    "B": "gpt-5.6-terra",
                }
            }
        },
    )
    assert summary["exploratory"] is True
    assert summary["n_scored"] == 1
    assert summary["pairwise_wins_by_model"]["gpt-5.6-terra"] == 1
    assert summary["average_by_model"]["gpt-5.6-terra"]["overall"] == 5
    assert summary["average_by_model"]["gpt-5.6-luna"]["overall"] == 4


def test_cli_exposes_rescore_and_summarize() -> None:
    parser = build_parser()
    rescore = parser.parse_args(["--rescore-bakeoff"])
    assert rescore.rescore_bakeoff == "DEFAULT"
    summary = parser.parse_args(
        ["--summarize-review", "review.md", "--reveal", "reveal.json"]
    )
    assert summary.summarize_review == "review.md"
    assert summary.reveal == "reveal.json"


def test_production_default_still_terra() -> None:
    assert DEFAULT_OPENAI_MODEL == "gpt-5.6-terra"


def test_rescore_original_luna_case5_if_artifact_present(tmp_path) -> None:
    if not ORIGINAL.exists():
        return
    paths = rescore_terra_luna_artifact(ORIGINAL, output_dir=tmp_path)
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["new_live_calls"] == 0
    assert payload["source_artifact"] == ORIGINAL.name
    luna = payload["luna_case_5"]
    assert luna["current_safety_ok"] is True
    assert luna["model_quality_hard_failures"] == []
    assert luna["original_hard_failures"] == ["unsafe_content"]
    assert luna["original_failure_owner"] == (
        FailureOwner.APPLICATION_VALIDATOR_FALSE_POSITIVE.value
    )
    assert payload["summary"]["by_model"]["gpt-5.6-luna"]["hard_failure_cases"] == 0
    assert payload["summary"]["by_model"]["gpt-5.6-terra"]["hard_failure_cases"] == 0
    assert payload["production_default_unchanged"] is True
    assert payload["routing_implemented"] is False
    review = paths["review"].read_text(encoding="utf-8")
    assert "Authoritative InstructionPlan" in review
    assert "Would use with my child" in review
    assert "gpt-5.6-terra" not in review
    assert "gpt-5.6-luna" not in review
    assert ORIGINAL.exists()
