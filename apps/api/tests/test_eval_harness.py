from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.ai.schemas import DailyWinGenerationResult
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.eval.fixtures import load_eval_fixtures
from daily_win_api.eval.runner import run_eval
from daily_win_api.eval.scoring import HUMAN_RUBRIC_KEYS, score_generation


def test_eval_catalog_is_synthetic_and_sized() -> None:
    fixtures = load_eval_fixtures()
    assert 15 <= len(fixtures) <= 25
    ids = [item.id for item in fixtures]
    assert len(ids) == len(set(ids))
    assert "nova_first" in ids
    assert "milo_first" in ids
    assert "riley_first" in ids
    ages = {item.context.parent_reported_baseline.age_years for item in fixtures}
    assert ages == {5, 6, 7, 8, 9}
    assert {item.win_kind for item in fixtures} == {"first", "adaptive"}
    assert {item.support for item in fixtures} == {"low", "medium", "high"}
    for item in fixtures:
        dumped = item.context.model_dump_json()
        assert "child_id" not in dumped
        assert "household_id" not in dumped


def test_score_generation_accepts_safe_fake_draft() -> None:
    fixture = next(item for item in load_eval_fixtures() if item.id == "hayes_first")
    result = DailyWinGenerationResult(
        draft=valid_daily_win_draft(),
        provider="fake",
        model="fake-model",
        prompt_version=PROMPT_VERSION,
        input_tokens=11,
        output_tokens=22,
        total_tokens=33,
        latency_ms=5,
    )
    scored = score_generation(fixture, result)
    by_name = {check.name: check.passed for check in scored.checks}
    assert by_name["schema_validity"] is True
    assert by_name["deterministic_safety"] is True
    assert by_name["instruction_plan_alignment"] is True
    assert by_name["learn_do_grow"] is True
    assert set(scored.human_rubric) == set(HUMAN_RUBRIC_KEYS)


def test_fake_eval_sample_writes_outside_learner_tables(tmp_path) -> None:
    path = run_eval(
        sample=1,
        fixture_ids=None,
        live=False,
        model=DEFAULT_OPENAI_MODEL,
        output_dir=tmp_path,
    )
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "canonical learner memory" in text
    assert '"live": false' in text


def test_fake_eval_runs_nova_fixture(tmp_path) -> None:
    path = run_eval(
        sample=None,
        fixture_ids=["nova_first", "milo_first", "riley_first"],
        live=False,
        model=DEFAULT_OPENAI_MODEL,
        output_dir=tmp_path,
    )
    text = path.read_text(encoding="utf-8")
    assert '"live": false' in text
    assert "nova_first" in text
    assert "milo_first" in text
    assert "riley_first" in text
