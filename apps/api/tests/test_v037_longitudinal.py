from daily_win_api.domains.learning.academic import project_academic_band
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.eval.builders import evidence
from daily_win_api.eval.longitudinal import (
    ARCHETYPES,
    cold_start_plan,
    contradiction_audit,
    detect_anomalies,
    goal_allocation_audit,
    recency_audit,
    simulate,
    step_down_audit,
    step_up_audit,
)
from daily_win_api.eval.policy_regression import evaluate_policy_regression
from daily_win_api.eval.suites import run_longitudinal_eval_suite


def test_policy_regression_matches_frozen_v1_decisions() -> None:
    assert evaluate_policy_regression() == []


def test_strong_and_developing_and_foundational_archetypes() -> None:
    fast = simulate(
        next(item for item in ARCHETYPES if item.id == "A"), weeks=4, wins_per_week=3
    )
    typical = simulate(
        next(item for item in ARCHETYPES if item.id == "B"), weeks=4, wins_per_week=3
    )
    gap = simulate(
        next(item for item in ARCHETYPES if item.id == "C"), weeks=6, wins_per_week=3
    )
    assert fast.wins
    assert typical.wins
    assert gap.wins[0].plan.primary_skill_code != "writing.spelling.cvc"
    assert "writing.spelling.cvc" in {
        item.plan.primary_skill_code for item in gap.wins
    } or gap.wins[0].plan.primary_skill_code.endswith("irregular")


def test_contradictory_sparse_frequent_and_age_starts() -> None:
    inconsistent = simulate(
        next(item for item in ARCHETYPES if item.id == "D"), weeks=4, wins_per_week=3
    )
    sparse = simulate(
        next(item for item in ARCHETYPES if item.id == "G"), weeks=8, wins_per_week=1
    )
    frequent = simulate(
        next(item for item in ARCHETYPES if item.id == "H"), weeks=4, wins_per_week=5
    )
    assert inconsistent.wins
    assert sparse.wins
    assert len(frequent.wins) == 20
    older = cold_start_plan(9, "writing.spelling")
    younger = cold_start_plan(5, "writing.spelling")
    assert older.primary_skill_code == "writing.spelling.multisyllabic_irregular"
    assert younger.primary_skill_code == "writing.spelling.cvc"
    math_plan = cold_start_plan(9, "math.addition")
    reading_plan = cold_start_plan(9, "reading.comprehension")
    assert math_plan.primary_skill_code == "math.addition.word_problems"
    assert reading_plan.primary_skill_code == "reading.comprehension.simple_inference"


def test_age9_spelling_descent_does_not_dump_to_kindergarten() -> None:
    audit = step_down_audit()
    assert audit["dumped_to_kindergarten"] is False
    assert audit["first_skill"] != "writing.spelling.cvc"


def test_age9_spelling_strong_diagnostic_does_not_repeat_forever() -> None:
    audit = step_up_audit()
    assert audit["first_skill"] == "writing.spelling.multisyllabic_irregular"
    assert audit["repeated_diagnostic_count"] <= 4


def test_anomaly_detectors_skill_loop_ping_pong_traps() -> None:
    fast = simulate(
        next(item for item in ARCHETYPES if item.id == "A"), weeks=2, wins_per_week=3
    )
    codes = {item.code for item in detect_anomalies(fast)}
    assert "PING_PONG" not in codes
    recency = recency_audit()
    assert recency["old_strong_plus_one_incorrect"]["needs_remediation"] is False
    contradiction = contradiction_audit()
    assert (
        contradiction["independent_independent_incorrect"]["needs_remediation"] is False
    )
    assert contradiction["retained_then_incorrect_help"]["needs_remediation"] is True
    alloc = goal_allocation_audit()
    assert alloc["math"] > 0
    assert alloc["spelling"] > alloc["math"]
    assert "instruction_scheduler_v1" in alloc["policy"]


def test_interest_change_does_not_change_instruction() -> None:
    learner = next(item for item in ARCHETYPES if item.id == "B")
    soccer = simulate(learner, weeks=3, wins_per_week=3, interests=("soccer",))
    space = simulate(learner, weeks=3, wins_per_week=3, interests=("space",))
    for left, right in zip(soccer.wins, space.wins, strict=False):
        assert left.plan.primary_skill_code == right.plan.primary_skill_code
        assert left.plan.scaffold_level == right.plan.scaffold_level
        assert left.plan.intended_difficulty == right.plan.intended_difficulty
        assert (
            left.plan.assessment_probe["observable_task"]
            == right.plan.assessment_probe["observable_task"]
        )


def test_projector_one_incorrect_does_not_oscillate() -> None:
    items = [
        evidence(AcademicResult.CORRECT_INDEPENDENTLY, day=-14, session="a"),
        evidence(AcademicResult.CORRECT_INDEPENDENTLY, day=-7, session="b"),
        evidence(AcademicResult.INCORRECT, day=0, session="c"),
    ]
    snapshot = project_academic_band(items, now=items[-1].occurred_at)
    assert snapshot.band in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}
    assert snapshot.needs_remediation is False


def test_longitudinal_suite_has_no_critical_failures() -> None:
    result = run_longitudinal_eval_suite()
    assert result.passed, result.errors
