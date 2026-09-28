from daily_win_api.domains.learning.enums import AcademicBand, InstructionMode
from daily_win_api.domains.learning.planner import plan_instruction
from daily_win_api.domains.learning.scheduler import schedule_instruction
from daily_win_api.eval.builders import planner_input, state

GOALS = (
    ("math.addition", 1),
    ("writing.spelling", 2),
    ("reading.comprehension", 3),
    ("growth.persistence", 4),
)


def test_discovery_covers_three_academic_domains() -> None:
    first = schedule_instruction(planner_input(age_years=9, grade="4", goals=GOALS))
    second = schedule_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=GOALS,
            recent_goals=(first.selected_goal_code,),
            recent_modes=("diagnostic",),
        )
    )
    third = schedule_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=GOALS,
            recent_goals=(second.selected_goal_code, first.selected_goal_code),
            recent_modes=("diagnostic", "diagnostic"),
        )
    )
    selected = {
        first.selected_goal_code,
        second.selected_goal_code,
        third.selected_goal_code,
    }
    assert selected == {"math.addition", "writing.spelling", "reading.comprehension"}
    assert "discovery_cycle" in second.selection_reason_codes
    assert first.discovery_cycle is False
    assert second.discovery_cycle is True


def test_discovery_does_not_monopolize_priority_one() -> None:
    second = schedule_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=GOALS,
            recent_goals=("math.addition",),
            recent_modes=("diagnostic",),
        )
    )
    assert second.selected_goal_code != "math.addition"


def test_discovery_uses_placement_diagnostic() -> None:
    plan = plan_instruction(planner_input(age_years=9, grade="4", goals=GOALS))
    assert plan.instruction_mode is InstructionMode.DIAGNOSTIC
    assert plan.coach_protocol is not None
    assert plan.coach_protocol["prompt_ceiling"] == "wait"


def test_discovery_exits_once_domains_have_evidence() -> None:
    math_leaves = (
        "math.addition.within_10",
        "math.addition.within_20",
        "math.addition.word_problems",
    )
    writing_leaves = (
        "writing.spelling.cvc",
        "writing.spelling.patterns",
        "writing.spelling.endings_suffixes",
        "writing.spelling.multisyllabic_irregular",
    )
    reading_leaves = (
        "reading.comprehension.recall_details",
        "reading.comprehension.main_idea",
        "reading.comprehension.simple_inference",
    )
    placed = planner_input(
        age_years=9,
        grade="4",
        goals=GOALS,
        states=tuple(
            state(code, AcademicBand.DEVELOPING, sessions=2)
            for code in (*math_leaves, *writing_leaves, *reading_leaves)
        ),
        recent_goals=("reading.comprehension", "writing.spelling", "math.addition"),
        recent_modes=("practice", "practice", "practice"),
    )
    focus = schedule_instruction(placed)
    assert "discovery_cycle" not in focus.selection_reason_codes
    assert focus.urgency_class != "unresolved_diagnostic"
