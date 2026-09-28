"""Frozen policy-decision fixtures for future v2/v4 comparisons."""

from __future__ import annotations

from daily_win_api.domains.learning.enums import InstructionMode
from daily_win_api.domains.learning.planner import plan_instruction_v3
from daily_win_api.eval.builders import planner_input

# Frozen expected decisions for identical PlannerInput. Do not silently change.
POLICY_REGRESSION_CASES: tuple[dict[str, object], ...] = (
    {
        "id": "age9_spelling_no_evidence",
        "expected_skill": "writing.spelling.multisyllabic_irregular",
        "expected_mode": InstructionMode.DIAGNOSTIC.value,
        "input": {
            "age_years": 9,
            "grade": "4",
            "goals": (("writing.spelling", 1), ("growth.persistence", 2)),
        },
    },
    {
        "id": "age5_spelling_no_evidence",
        "expected_skill": "writing.spelling.cvc",
        "expected_mode": InstructionMode.INTRODUCE.value,
        "input": {
            "age_years": 5,
            "grade": "K",
            "goals": (("writing.spelling", 1), ("growth.persistence", 2)),
        },
    },
    {
        "id": "age9_math_no_evidence",
        "expected_skill": "math.addition.word_problems",
        "expected_mode": InstructionMode.DIAGNOSTIC.value,
        "input": {
            "age_years": 9,
            "grade": "4",
            "goals": (("math.addition", 1), ("growth.persistence", 2)),
        },
    },
    {
        "id": "age9_reading_no_evidence",
        "expected_skill": "reading.comprehension.simple_inference",
        "expected_mode": InstructionMode.DIAGNOSTIC.value,
        "input": {
            "age_years": 9,
            "grade": "4",
            "goals": (("reading.comprehension", 1), ("growth.persistence", 2)),
        },
    },
)


def evaluate_policy_regression() -> list[str]:
    errors: list[str] = []
    for case in POLICY_REGRESSION_CASES:
        payload = dict(case["input"])
        data = planner_input(
            age_years=int(payload["age_years"]),
            grade=str(payload["grade"]),
            goals=tuple(payload["goals"]),
            states=(),
        )
        plan = plan_instruction_v3(data)
        if plan.primary_skill_code != case["expected_skill"]:
            errors.append(
                f"{case['id']} skill {plan.primary_skill_code} != "
                f"{case['expected_skill']}"
            )
        if plan.instruction_mode.value != case["expected_mode"]:
            errors.append(
                f"{case['id']} mode {plan.instruction_mode.value} != "
                f"{case['expected_mode']}"
            )
    return errors
