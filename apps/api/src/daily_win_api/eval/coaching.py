"""Offline coaching, discovery, and weekly-report eval. No live model."""

from __future__ import annotations

from datetime import UTC, datetime

from daily_win_api.domains.learning.bonus import bonus_is_not_academic, choose_bonus
from daily_win_api.domains.learning.challenge import PRODUCTIVE, classify_challenge
from daily_win_api.domains.learning.coach_protocol import (
    COACH_PROTOCOL_V1,
    LEVEL_LIGHT_CUE,
    LEVEL_MODEL,
    LEVEL_REDUCE,
    LEVEL_STRATEGY,
    LEVEL_WAIT,
    build_coach_protocol,
    contains_banned_coaching,
)
from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel
from daily_win_api.domains.learning.observations import (
    SELF_CORRECTION_IS_NOT_FIRST_ATTEMPT,
)
from daily_win_api.domains.learning.planner import plan_instruction, plan_instruction_v3
from daily_win_api.domains.learning.scheduler import schedule_instruction
from daily_win_api.domains.learning.weekly import (
    BANNED_WEEKLY_CLAIMS,
    SessionEvidence,
    synthesize_week,
    weekly_text_is_safe,
)
from daily_win_api.eval.builders import planner_input

EVAL_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

DISCOVERY_GOALS = (
    ("math.addition", 1),
    ("writing.spelling", 2),
    ("reading.comprehension", 3),
    ("growth.persistence", 4),
)


def coaching_errors() -> list[str]:
    errors: list[str] = []
    errors.extend(_protocol_mode_errors())
    errors.extend(_discovery_errors())
    errors.extend(_weekly_golden_errors())
    errors.extend(_packet_replacement_errors())
    errors.extend(_bonus_errors())
    errors.extend(_privacy_errors())
    return errors


def _protocol_mode_errors() -> list[str]:
    errors: list[str] = []
    expected = {
        InstructionMode.DIAGNOSTIC: LEVEL_WAIT,
        InstructionMode.INTRODUCE: LEVEL_MODEL,
        InstructionMode.PRACTICE: LEVEL_STRATEGY,
        InstructionMode.REMEDIATION: LEVEL_REDUCE,
        InstructionMode.REVIEW: LEVEL_LIGHT_CUE,
    }
    for mode, ceiling in expected.items():
        protocol = build_coach_protocol(
            instruction_mode=mode,
            scaffold=ScaffoldLevel.MEDIUM,
            age_years=9,
            skill_code="math.addition.within_20",
            academic_band=None,
            growth_target_code="growth.persistence",
        )
        if protocol.protocol_version != COACH_PROTOCOL_V1:
            errors.append(f"{mode.value}: version")
        if protocol.prompt_ceiling != ceiling:
            errors.append(f"{mode.value}: ceiling {protocol.prompt_ceiling}")
        if mode is InstructionMode.DIAGNOSTIC:
            if "Do not teach" not in protocol.assessment_boundary:
                errors.append("diagnostic missing no-teach boundary")
            if protocol.teach_the_coach:
                errors.append("diagnostic should not teach-the-coach")
        blob = " ".join(protocol.coach_card)
        if contains_banned_coaching(blob):
            errors.append(f"{mode.value}: banned coaching")
        if len(protocol.coach_card) > 3:
            errors.append(f"{mode.value}: coach card too long")
    young = build_coach_protocol(
        instruction_mode=InstructionMode.PRACTICE,
        scaffold=ScaffoldLevel.HIGH,
        age_years=6,
        skill_code="writing.spelling.cvc",
        academic_band="emerging",
        growth_target_code=None,
    )
    if young.one_thing_to_improve is None:
        errors.append("writing missing one-thing-to-improve")
    if young.independence_goal == "More independent reasoning.":
        errors.append("younger coaching should stay concrete")
    return errors


def _discovery_errors() -> list[str]:
    errors: list[str] = []
    first = schedule_instruction(
        planner_input(age_years=9, grade="4", goals=DISCOVERY_GOALS)
    )
    if first.selected_goal_code != "math.addition":
        errors.append(f"discovery win1 {first.selected_goal_code}")
    second = schedule_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=DISCOVERY_GOALS,
            recent_goals=("math.addition",),
            recent_modes=("diagnostic",),
        )
    )
    if second.selected_goal_code == "math.addition":
        errors.append("discovery monopolized math")
    if "discovery_cycle" not in second.selection_reason_codes:
        errors.append("discovery missing reason")
    third = schedule_instruction(
        planner_input(
            age_years=9,
            grade="4",
            goals=DISCOVERY_GOALS,
            recent_goals=("writing.spelling", "math.addition"),
            recent_modes=("diagnostic", "diagnostic"),
        )
    )
    if third.selected_goal_code != "reading.comprehension":
        errors.append(f"discovery win3 {third.selected_goal_code}")
    plan = plan_instruction(
        planner_input(age_years=9, grade="4", goals=DISCOVERY_GOALS)
    )
    if plan.coach_protocol is None:
        errors.append("v4 plan missing coach protocol")
    if plan.instruction_mode.value != "diagnostic":
        errors.append("discovery first plan should be diagnostic")
    v3 = plan_instruction_v3(
        planner_input(age_years=9, grade="4", goals=DISCOVERY_GOALS)
    )
    if v3.coach_protocol is not None:
        errors.append("historical v3 gained a fake CoachProtocol")
    return errors


def _weekly_golden_errors() -> list[str]:
    errors: list[str] = []
    cases = {
        "A": _case_math_strong_writing_weak(),
        "B": _case_academic_strong_persistence_weak(),
        "C": _case_academic_weak_persistence_strong(),
        "D": _case_everything_easy(),
        "E": _case_contradictory(),
        "F": _case_dislikes_mechanic(),
    }
    for name, sessions in cases.items():
        summary = synthesize_week(
            sessions, week_start=EVAL_NOW, week_end=EVAL_NOW
        )
        blob = " ".join(
            [
                *summary.what_looked_strong,
                *summary.what_still_took_work,
                *summary.how_they_handled_challenge,
                *summary.what_they_enjoyed,
                summary.parent_coaching_suggestion,
            ]
        ).lower()
        if not weekly_text_is_safe(blob):
            errors.append(f"{name}: banned weekly language")
        for phrase in BANNED_WEEKLY_CLAIMS:
            if phrase in blob:
                errors.append(f"{name}: {phrase}")
        if name == "A" and not any(
            "writing" in item.lower() for item in summary.what_still_took_work
        ):
            errors.append("A missing writing support claim")
        if name == "A" and not any(
            "math" in item.lower() for item in summary.what_looked_strong
        ):
            errors.append("A missing math strength")
        if name == "F" and not any(
            "low-engagement" in item.lower() for item in summary.what_they_enjoyed
        ):
            if not summary.engagement_memory.low_engagement_categories:
                errors.append("F missing repeated low engagement")
        if name == "E" and not any(
            "not enough" in item.lower()
            or "relative" in item.lower()
            or "still" in item.lower()
            for item in (*summary.what_looked_strong, *summary.what_still_took_work)
        ):
            errors.append("E should stay cautious")
        if not summary.claims_trace:
            errors.append(f"{name}: missing claim traces")
    return errors


def _packet_replacement_errors() -> list[str]:
    errors: list[str] = []
    sessions = (
        SessionEvidence(
            skill_code="math.addition.within_20",
            instruction_mode="diagnostic",
            academic_result="correct_independently",
            difficulty="about_right",
            performance_effort="automatic",
            self_correction="not_observed",
            setback_response="no_setback_occurred",
            source_keys=("s1",),
        ),
        SessionEvidence(
            skill_code="writing.spelling.endings_suffixes",
            instruction_mode="practice",
            academic_result="correct_after_light_prompt",
            difficulty="too_hard",
            performance_effort="effortful_with_support",
            self_correction="self_corrected",
            setback_response="continued_after_prompt",
            strategy="used_known_pattern",
            source_keys=("s2",),
        ),
        SessionEvidence(
            skill_code="reading.comprehension.retell",
            instruction_mode="practice",
            academic_result="correct_independently",
            teach_the_coach=True,
            setback_response="kept_going_independently",
            source_keys=("s3",),
        ),
        SessionEvidence(
            skill_code="math.addition.word_problems",
            instruction_mode="practice",
            academic_result="correct_independently",
            setback_response="kept_going_independently",
            personal_best=True,
            source_keys=("s4",),
        ),
        SessionEvidence(
            skill_code="writing.organization.sequence",
            instruction_mode="practice",
            academic_result="correct_after_significant_help",
            bonus_category="physical",
            bonus_engagement="not_into_it",
            setback_response="needed_significant_help",
            source_keys=("s5",),
        ),
    )
    summary = synthesize_week(sessions, week_start=EVAL_NOW, week_end=EVAL_NOW)
    needed = (
        summary.what_looked_strong,
        summary.what_still_took_work,
        summary.how_they_handled_challenge,
        summary.what_they_enjoyed,
        summary.what_changes_next_week,
    )
    if any(not item for item in needed):
        errors.append("packet replacement missing a weekly section")
    if summary.wins_completed != 5:
        errors.append("packet replacement win count")
    if not summary.parent_coaching_suggestion:
        errors.append("packet replacement missing parent suggestion")
    challenge = classify_challenge(
        difficulty="about_right",
        academic_result="correct_independently",
        performance_effort="effortful_but_independent",
        setback_response="continued_after_prompt",
        completion="completed",
    )
    if challenge != PRODUCTIVE:
        errors.append("productive challenge misclassified")
    if "first-attempt" in SELF_CORRECTION_IS_NOT_FIRST_ATTEMPT.lower():
        pass
    return errors


def _bonus_errors() -> list[str]:
    errors: list[str] = []
    bonus = choose_bonus(
        primary_skill_code="math.addition.within_10",
        teach_the_coach=True,
        age_years=9,
    )
    if bonus.counts_as_mastery:
        errors.append("bonus counted as mastery")
    if not bonus.optional:
        errors.append("bonus not optional")
    if not bonus_is_not_academic(bonus.code):
        errors.append("bonus looked academic")
    skipped = choose_bonus(
        primary_skill_code="math.addition.within_10",
        teach_the_coach=False,
        low_engagement_categories=("memory",),
        age_years=9,
    )
    if skipped.category == "memory":
        errors.append("low-engagement mechanic reused immediately")
    return errors


def _privacy_errors() -> list[str]:
    errors: list[str] = []
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    forbidden = ("report card", "handwritten packet", "real child notes")
    for path in (root / "docs").glob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        if "daily win is alpha at home" in text or "proven alpha method" in text:
            errors.append(f"{path.name} makes equivalent-outcome claims")
    fixtures = root / "apps" / "api" / "src" / "daily_win_api" / "eval"
    blob = "\n".join(path.read_text(encoding="utf-8") for path in fixtures.glob("*.py"))
    for item in forbidden:
        if item in blob.lower():
            errors.append(f"eval fixtures mention {item}")
    return errors


def _case_math_strong_writing_weak() -> tuple[SessionEvidence, ...]:
    return (
        SessionEvidence(
            skill_code="math.addition.within_20",
            instruction_mode="practice",
            academic_result="correct_independently",
            performance_effort="automatic",
            source_keys=("a1",),
        ),
        SessionEvidence(
            skill_code="math.addition.word_problems",
            instruction_mode="practice",
            academic_result="correct_independently",
            source_keys=("a2",),
        ),
        SessionEvidence(
            skill_code="writing.spelling.endings_suffixes",
            instruction_mode="practice",
            academic_result="correct_after_significant_help",
            performance_effort="effortful_with_support",
            source_keys=("a3",),
        ),
    )


def _case_academic_strong_persistence_weak() -> tuple[SessionEvidence, ...]:
    return (
        SessionEvidence(
            skill_code="math.addition.within_20",
            instruction_mode="practice",
            academic_result="correct_independently",
            setback_response="stopped_or_avoided",
            source_keys=("b1",),
        ),
        SessionEvidence(
            skill_code="reading.comprehension.retell",
            instruction_mode="practice",
            academic_result="correct_independently",
            setback_response="stopped_or_avoided",
            source_keys=("b2",),
        ),
    )


def _case_academic_weak_persistence_strong() -> tuple[SessionEvidence, ...]:
    return (
        SessionEvidence(
            skill_code="writing.spelling.cvc",
            instruction_mode="remediation",
            academic_result="incorrect",
            setback_response="kept_going_independently",
            source_keys=("c1",),
        ),
        SessionEvidence(
            skill_code="math.addition.within_10",
            instruction_mode="practice",
            academic_result="correct_after_significant_help",
            setback_response="kept_going_independently",
            source_keys=("c2",),
        ),
    )


def _case_everything_easy() -> tuple[SessionEvidence, ...]:
    return tuple(
        SessionEvidence(
            skill_code="math.addition.within_10",
            instruction_mode="practice",
            academic_result="correct_independently",
            difficulty="too_easy",
            performance_effort="automatic",
            source_keys=(f"d{index}",),
        )
        for index in range(3)
    )


def _case_contradictory() -> tuple[SessionEvidence, ...]:
    return (
        SessionEvidence(
            skill_code="math.addition.within_20",
            instruction_mode="practice",
            academic_result="correct_independently",
            source_keys=("e1",),
        ),
        SessionEvidence(
            skill_code="math.addition.within_20",
            instruction_mode="practice",
            academic_result="incorrect",
            source_keys=("e2",),
        ),
    )


def _case_dislikes_mechanic() -> tuple[SessionEvidence, ...]:
    return (
        SessionEvidence(
            skill_code="math.addition.within_10",
            instruction_mode="practice",
            academic_result="correct_independently",
            bonus_category="physical",
            bonus_engagement="not_into_it",
            source_keys=("f1",),
        ),
        SessionEvidence(
            skill_code="writing.spelling.cvc",
            instruction_mode="practice",
            academic_result="correct_independently",
            bonus_category="physical",
            bonus_engagement="not_into_it",
            source_keys=("f2",),
        ),
    )
