from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from daily_win_api.core.demo import get_demo_child
from daily_win_api.db.session import engine
from daily_win_api.domains.learning.academic import (
    AcademicEvidence,
    project_academic_band,
)
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    AcademicResult,
    InstructionMode,
)
from daily_win_api.domains.learning.explanations import why_not_explanations
from daily_win_api.domains.learning.observatory import build_next_win_preview
from daily_win_api.domains.learning.planner import (
    INSTRUCTION_POLICY_V3,
    INSTRUCTION_POLICY_V4,
    plan_from_dict,
    plan_instruction,
    plan_instruction_v3,
)
from daily_win_api.domains.learning.scheduler import (
    CONSECUTIVE_FOCUS_LIMIT,
    INSTRUCTION_SCHEDULER_V1,
    MAX_GOAL_NEGLECT_WINDOW,
    classify_goal_urgency,
    schedule_instruction,
)
from daily_win_api.eval.builders import planner_input, state
from daily_win_api.eval.longitudinal import (
    CONFLICT_ARCHETYPES,
    scheduler_before_after,
    simulate,
)

SPELLING_LEAVES = (
    "writing.spelling.cvc",
    "writing.spelling.patterns",
    "writing.spelling.endings_suffixes",
    "writing.spelling.multisyllabic_irregular",
)
MATH_LEAVES = (
    "math.addition.within_10",
    "math.addition.within_20",
    "math.addition.word_problems",
)
MULTI_GOALS = (
    ("writing.spelling", 1),
    ("math.addition", 2),
    ("growth.persistence", 3),
)


def _retained(code: str, *, days: int = 3) -> object:
    return state(
        code,
        AcademicBand.RETAINED,
        sessions=3,
        practiced_days_ago=days,
        independent_days_ago=days,
    )


def _developing(code: str) -> object:
    return state(code, AcademicBand.DEVELOPING, sessions=2, practiced_days_ago=1)


def _remediating(code: str) -> object:
    return state(
        code,
        AcademicBand.EMERGING,
        sessions=2,
        practiced_days_ago=0,
        needs_remediation=True,
    )


def test_scheduler_is_deterministic() -> None:
    data = planner_input(goals=MULTI_GOALS)
    first = schedule_instruction(data)
    second = schedule_instruction(data)
    assert first == second
    assert first.scheduler_version == INSTRUCTION_SCHEDULER_V1
    assert first.selected_goal_code == "writing.spelling"


def test_priority_one_is_preferred_not_monopoly() -> None:
    data = planner_input(goals=MULTI_GOALS)
    focus = schedule_instruction(data)
    assert focus.selected_goal_code == "writing.spelling"
    assert "highest_priority" in focus.selection_reason_codes
    rotated = schedule_instruction(
        planner_input(
            goals=MULTI_GOALS,
            recent_goals=("writing.spelling",) * CONSECUTIVE_FOCUS_LIMIT,
            recent_modes=("practice",) * CONSECUTIVE_FOCUS_LIMIT,
        )
    )
    assert rotated.selected_goal_code == "math.addition"
    assert "consecutive_focus_limit" in rotated.selection_reason_codes or (
        "new_goal_needs_placement" in rotated.selection_reason_codes
        or "discovery_cycle" in rotated.selection_reason_codes
    )


def test_secondary_goal_starvation_guard() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        recent_goals=("writing.spelling",) * MAX_GOAL_NEGLECT_WINDOW,
        recent_modes=("practice",) * MAX_GOAL_NEGLECT_WINDOW,
    )
    focus = schedule_instruction(data)
    assert focus.selected_goal_code == "math.addition"
    assert focus.starvation_guard_triggered is True
    assert "secondary_goal_starvation_guard" in focus.selection_reason_codes


def test_remediation_urgency_and_escape() -> None:
    weak = planner_input(
        goals=MULTI_GOALS,
        states=(
            _remediating("writing.spelling.cvc"),
            _developing("math.addition.within_10"),
        ),
    )
    focus = schedule_instruction(weak)
    assert focus.selected_goal_code == "writing.spelling"
    assert focus.urgency_class == "active_remediation"
    recovered = planner_input(
        goals=MULTI_GOALS,
        states=(
            state("writing.spelling.cvc", AcademicBand.DEVELOPING, sessions=3),
            _developing("math.addition.within_10"),
        ),
        recent_goals=("writing.spelling",) * CONSECUTIVE_FOCUS_LIMIT,
        recent_modes=("remediation",) * CONSECUTIVE_FOCUS_LIMIT,
    )
    after = schedule_instruction(recovered)
    assert after.selected_goal_code == "math.addition"
    assert after.urgency_class != "active_remediation"


def test_diagnostic_urgency_and_escape() -> None:
    cold = planner_input(age_years=9, grade="4", goals=MULTI_GOALS)
    focus = schedule_instruction(cold)
    assert focus.urgency_class == "unresolved_diagnostic"
    assert focus.selected_goal_code == "writing.spelling"
    placed = planner_input(
        age_years=9,
        grade="4",
        goals=MULTI_GOALS,
        states=(
            state(
                "writing.spelling.multisyllabic_irregular",
                AcademicBand.DEVELOPING,
                sessions=2,
            ),
            state("math.addition.word_problems", AcademicBand.DEVELOPING, sessions=2),
        ),
    )
    after = schedule_instruction(placed)
    assert after.urgency_class == "active_learning"
    assert classify_goal_urgency("writing.spelling", placed) == "active_learning"


def test_new_goal_needs_placement() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        recent_goals=("writing.spelling",) * CONSECUTIVE_FOCUS_LIMIT,
        recent_modes=("practice",) * CONSECUTIVE_FOCUS_LIMIT,
    )
    focus = schedule_instruction(data)
    assert focus.selected_goal_code == "math.addition"
    assert "new_goal_needs_placement" in focus.selection_reason_codes or (
        "secondary_goal_starvation_guard" in focus.selection_reason_codes
        or "consecutive_focus_limit" in focus.selection_reason_codes
        or "discovery_cycle" in focus.selection_reason_codes
    )


def test_retained_terminal_skill_moves_to_maintenance() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        states=tuple(_retained(code) for code in SPELLING_LEAVES)
        + tuple(_developing(code) for code in MATH_LEAVES),
    )
    focus = schedule_instruction(data)
    plan = plan_instruction(data)
    assert focus.selected_goal_code == "math.addition"
    assert focus.urgency_class == "active_learning"
    assert plan.primary_skill_code.startswith("math.")
    assert "writing.spelling" in plan.deferred_goals


def test_terminal_skill_does_not_ordinary_practice_loop() -> None:
    data = planner_input(
        goals=(("writing.spelling", 1), ("growth.persistence", 2)),
        states=tuple(_retained(code) for code in SPELLING_LEAVES),
        recent_skills=("writing.spelling.multisyllabic_irregular",) * 6,
        recent_modes=("practice",) * 6,
        recent_goals=("writing.spelling",) * 6,
    )
    plan = plan_instruction(data)
    assert plan.instruction_mode is InstructionMode.REVIEW
    assert "terminal_maintenance_transfer" in plan.selection_reason_codes
    assert plan.application_variant == "transfer"
    v3 = plan_instruction_v3(data)
    assert v3.policy_version == INSTRUCTION_POLICY_V3
    assert v3.scheduler_version is None


def test_review_is_candidate_not_mandatory() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        states=tuple(_retained(code, days=20) for code in SPELLING_LEAVES)
        + tuple(_developing(code) for code in MATH_LEAVES),
        recent_modes=("practice", "practice", "practice"),
        recent_goals=("math.addition", "math.addition", "math.addition"),
    )
    focus = schedule_instruction(data)
    assert focus.selected_goal_code == "math.addition"
    assert focus.review_due is False


def test_review_load_guard() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        states=tuple(_retained(code, days=20) for code in SPELLING_LEAVES)
        + tuple(_developing(code) for code in MATH_LEAVES),
        recent_modes=("review", "review", "practice"),
        recent_goals=("writing.spelling", "math.addition", "math.addition"),
        recent_skills=(
            "writing.spelling.multisyllabic_irregular",
            "math.addition.within_10",
            "math.addition.within_10",
        ),
    )
    focus = schedule_instruction(data)
    plan = plan_instruction(data)
    assert focus.selected_goal_code == "math.addition"
    assert plan.instruction_mode != InstructionMode.REVIEW
    assert "review_load_guard" in focus.selection_reason_codes


def test_review_cooldown_prevents_ping_pong() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        states=tuple(_retained(code, days=20) for code in SPELLING_LEAVES)
        + tuple(_retained(code, days=20) for code in MATH_LEAVES),
        recent_modes=("review", "review"),
        recent_goals=("writing.spelling", "math.addition"),
        recent_skills=(
            "writing.spelling.multisyllabic_irregular",
            "math.addition.word_problems",
        ),
    )
    focus = schedule_instruction(data)
    assert focus.selected_goal_code == "math.addition"


def test_growth_overlay_does_not_consume_academic_slot() -> None:
    plan = plan_instruction(planner_input(goals=MULTI_GOALS))
    assert plan.scheduled_goal_code == "writing.spelling"
    assert plan.growth_target_code == "growth.persistence"
    assert plan.primary_skill_code.startswith("writing.")


def test_goal_reorder_uses_new_priority_without_erasing_state() -> None:
    states = tuple(_developing(code) for code in (*SPELLING_LEAVES, *MATH_LEAVES))
    original = plan_instruction(planner_input(goals=MULTI_GOALS, states=states))
    reordered = plan_instruction(
        planner_input(
            goals=(
                ("math.addition", 1),
                ("writing.spelling", 2),
                ("growth.persistence", 3),
            ),
            states=states,
        )
    )
    assert original.scheduled_goal_code == "writing.spelling"
    assert reordered.scheduled_goal_code == "math.addition"
    assert reordered.policy_version == INSTRUCTION_POLICY_V4


def test_goal_removal_and_addition() -> None:
    remaining = plan_instruction(
        planner_input(goals=(("math.addition", 1), ("growth.persistence", 2)))
    )
    assert remaining.scheduled_goal_code == "math.addition"
    added = schedule_instruction(
        planner_input(
            goals=MULTI_GOALS,
            recent_goals=("writing.spelling",) * 3,
            recent_modes=("practice",) * 3,
        )
    )
    assert added.selected_goal_code == "math.addition"


def test_why_and_why_not_use_scheduler_metadata() -> None:
    data = planner_input(
        goals=MULTI_GOALS,
        recent_goals=("writing.spelling",) * MAX_GOAL_NEGLECT_WINDOW,
        recent_modes=("practice",) * MAX_GOAL_NEGLECT_WINDOW,
    )
    plan = plan_instruction(data)
    why = why_not_explanations(plan, data)
    assert plan.scheduler_why_selected
    assert why.why_not_second_goal
    assert why.why_not_review
    assert why.why_not_terminal
    selected = (plan.scheduler_why_selected or "").lower()
    second = why.why_not_second_goal.lower()
    assert "math" in selected or "math" in second


def test_scheduler_version_persists_and_historical_plans_load() -> None:
    plan = plan_instruction(planner_input(goals=MULTI_GOALS))
    assert plan.scheduler_version == INSTRUCTION_SCHEDULER_V1
    assert plan.policy_version == INSTRUCTION_POLICY_V4
    restored = plan_from_dict(
        {
            "primary_skill_code": "writing.spelling.cvc",
            "instruction_mode": "practice",
            "intended_difficulty": "similar",
            "scaffold_level": "one_prompt",
            "policy_version": "instruction_policy_v3",
            "selection_reason_codes": ["parent_priority"],
            "assessment_probe": {"observable_task": "spell a word"},
        }
    )
    assert restored.policy_version == "instruction_policy_v3"
    assert restored.scheduler_version is None
    assert restored.scheduled_goal_code is None


def test_profile_a_twelve_wins_prefers_spelling_but_serves_math() -> None:
    morgan = next(item for item in CONFLICT_ARCHETYPES if item.id == "M")
    history = simulate(morgan, weeks=4, wins_per_week=3)
    spelling = sum(
        1 for item in history.wins if "spelling" in item.plan.primary_skill_code
    )
    math = sum(
        1
        for item in history.wins
        if item.plan.primary_skill_code.startswith("math.")
    )
    overlays = sum(
        1
        for item in history.wins
        if item.plan.growth_target_code == "growth.persistence"
    )
    assert spelling > math
    assert math >= 2
    assert overlays == len(history.wins)
    assert not any(
        item.plan.primary_skill_code.startswith("growth.") for item in history.wins
    )


def test_profile_c_retained_terminal_gives_math_the_active_slot() -> None:
    data = planner_input(
        age_years=9,
        grade="4",
        goals=MULTI_GOALS,
        states=tuple(_retained(code) for code in SPELLING_LEAVES)
        + (_developing("math.addition.within_10"),),
    )
    plan = plan_instruction(data)
    assert plan.scheduled_goal_code == "math.addition"
    assert not plan.primary_skill_code.startswith("writing.spelling")


def test_v3_fixtures_remain_schedulerless() -> None:
    plan = plan_instruction_v3(planner_input(goals=MULTI_GOALS))
    assert plan.policy_version == INSTRUCTION_POLICY_V3
    assert plan.scheduler_version is None
    assert plan.scheduled_goal_code is None


def test_before_after_clears_v037_high_findings() -> None:
    compare = scheduler_before_after()
    multi = compare["multi_goal_20"]
    sparse = compare["sparse_reviews"]
    terminal = compare["terminal_spelling"]
    assert multi["old_math"] == 0
    assert multi["new_math"] > 0
    assert multi["new_spelling"] > multi["new_math"]
    assert multi["old_starvation"] is True
    assert multi["new_starvation"] is False
    assert sparse["new"] <= sparse["old"]
    assert sparse["new_ping_pong"] is False
    assert terminal["new_loop"] is False


def test_next_win_preview_includes_scheduler_fields(demo_db) -> None:
    from daily_win_api.ai.providers.fake import FakeModelGateway
    from daily_win_api.domains.daily_wins.service import generate_demo_daily_win

    generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    preview = build_next_win_preview(demo_db, child)
    assert preview.scheduled_goal
    assert preview.scheduler_reason
    assert preview.likely_target
    assert preview.likely_mode
    assert preview.likely_scaffold


def test_rebuild_benchmark_one_skill_evidence_counts() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    timings: dict[int, float] = {}
    for count in (100, 500, 1000):
        evidence = [
            AcademicEvidence(
                event_id=uuid4(),
                occurred_at=now - timedelta(days=count - index),
                result=AcademicResult.CORRECT_INDEPENDENTLY
                if index % 3
                else AcademicResult.CORRECT_AFTER_LIGHT_PROMPT,
                session_key=f"session-{index}",
            )
            for index in range(count)
        ]
        started = perf_counter()
        snapshot = project_academic_band(evidence, now=now)
        timings[count] = perf_counter() - started
        assert snapshot.algorithm_version == "academic_projector_v1"
        assert snapshot.usable_evidence_count == count
    assert timings[1000] < 2.0
    assert timings[100] <= timings[1000]


def test_uncommitted_wins_are_invisible_to_a_second_connection(demo_db) -> None:
    from daily_win_api.ai.providers.fake import FakeModelGateway
    from daily_win_api.domains.daily_wins.models import DailyWin
    from daily_win_api.domains.daily_wins.service import generate_demo_daily_win

    generated = generate_demo_daily_win(demo_db, FakeModelGateway())
    child = get_demo_child(demo_db)
    win = demo_db.get(DailyWin, generated.id)
    assert child is not None
    assert win is not None
    with Session(bind=engine) as other:
        unseen = other.get(DailyWin, win.id)
    assert unseen is None


def test_sparse_multi_goal_reviews_do_not_monopolize() -> None:
    morgan = next(item for item in CONFLICT_ARCHETYPES if item.id == "M")
    history = simulate(morgan, weeks=24, wins_per_week=1)
    reviews = sum(
        1 for item in history.wins if item.plan.instruction_mode.value == "review"
    )
    math = sum(
        1
        for item in history.wins
        if item.plan.primary_skill_code.startswith("math.")
    )
    assert math > 0
    assert reviews <= 12
