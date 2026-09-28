"""Labelled renderer-contract fixtures from V0.3.4 blind review cases 1–8."""

from __future__ import annotations

from dataclasses import dataclass

from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.ai.schemas import DailyWinDraft, InstructionPlanContext
from daily_win_api.domains.daily_wins.renderer_contract import (
    AGE_RESPECTFUL_FOUNDATION,
    DIAGNOSTIC_PROBE_BEFORE_TEACHING,
    FRESH_ASSESSMENT_ITEM,
    GROWTH_OVERLAY_DISCONNECTED,
    ONE_CANONICAL_ASSESSMENT,
    PRIMARY_SKILL_TIME_MAJORITY,
    REVIEW_PRACTICE_THEN_CHECK,
    SECTION_DURATION_IMPLAUSIBLE,
    THREE_CONCRETE_CUES,
)


@dataclass(frozen=True)
class RendererContractCase:
    id: str
    label: str
    draft: DailyWinDraft
    plan: InstructionPlanContext
    expect_hard: str | None
    expect_soft: str | None


def _plan(**overrides: object) -> InstructionPlanContext:
    primary = str(overrides.get("primary_skill_code") or "math.addition.within_10")
    payload: dict[str, object] = {
        "primary_skill_code": primary,
        "supporting_skill_code": None,
        "selection_reason_codes": ["parent_priority"],
        "instruction_mode": "introduce",
        "intended_difficulty": "similar",
        "scaffold_level": "one_prompt",
        "prerequisite_rationale": "Blind-review fixture.",
        "assessment_objective": "Observe one independent try at the planned skill.",
        "assessment_probe": {
            "target_skill_code": primary,
            "observable_task": "Ask one addition fact whose sum is 10 or less.",
            "expected_outcome": "Child states the correct sum.",
        },
        "desired_evidence": "structured academic result plus parent observation",
        "growth_target_code": None,
        "duration_minutes": 18,
        "policy_version": "instruction_policy_v2",
        "academic_band": "not_observed",
    }
    payload.update(overrides)
    return InstructionPlanContext.model_validate(payload)


def _draft(
    *,
    learn_steps: list[str],
    learn_minutes: int = 6,
    learn_title: str = "Learn",
    do_steps: list[str] | None = None,
    do_minutes: int = 7,
    do_title: str = "Do",
    grow_steps: list[str] | None = None,
    grow_minutes: int = 5,
    duration: int = 18,
    observation: str | None = None,
    primary_skill_code: str = "math.addition.within_10",
    supporting: list[str] | None = None,
) -> DailyWinDraft:
    base = valid_daily_win_draft(
        primary_skill_code=primary_skill_code,
        supporting_skill_codes=supporting or ["growth.persistence"],
    )
    learn, do, grow = base.segments
    return base.model_copy(
        update={
            "duration_minutes": duration,
            "observation_focus": observation
            or "WHAT TO CHECK: one independent addition fact within 10.",
            "segments": [
                learn.model_copy(
                    update={
                        "title": learn_title,
                        "minutes": learn_minutes,
                        "steps": learn_steps,
                    }
                ),
                do.model_copy(
                    update={
                        "title": do_title,
                        "minutes": do_minutes,
                        "steps": do_steps
                        or ["Keep the same addition work going with a movement."],
                    }
                ),
                grow.model_copy(
                    update={
                        "minutes": grow_minutes,
                        "steps": grow_steps
                        or [
                            "After a hard fact, pause and ask what to try next.",
                            "Name the effort, then return to one more fact.",
                        ],
                    }
                ),
            ],
        }
    )


def labelled_renderer_contract_cases() -> tuple[RendererContractCase, ...]:
    good_three = _draft(
        learn_title="Three cues",
        learn_steps=[
            "Touch the first addend.",
            "Say the sum out loud.",
            "Move the counters together.",
        ],
    )
    bad_three = _draft(
        learn_title="Visual process",
        learn_steps=[
            "Follow a three-step visual process to add the numbers together.",
            "Then they can try on their own when ready.",
        ],
    )
    three_plan = _plan(scaffold_level="three_step_visual")

    good_fresh = _draft(
        learn_steps=[
            "Practice 4+3 with counters.",
            "Try one more practice fact: 2+5.",
            "WHAT TO CHECK: ask 6+1 independently.",
        ],
        observation="WHAT TO CHECK: independent 6+1.",
    )
    bad_fresh = _draft(
        learn_steps=[
            "Practice 4+3 with counters.",
            "Ask 4+3 again as the check.",
        ],
        observation="Check 4+3 one more time.",
    )
    item_plan = _plan(
        instruction_mode="practice",
        primary_skill_code="math.addition.within_10",
    )

    diagnostic_plan = _plan(instruction_mode="diagnostic")
    good_diagnostic = _draft(
        learn_steps=[
            "Ask one addition fact whose sum is 10 or less.",
            "If needed, show how to count objects after that probe.",
            "Practice one different fact together.",
        ],
        observation="WHAT TO CHECK: the first independent fact only.",
    )
    bad_diagnostic = _draft(
        learn_steps=[
            "Show how to add 4+3 with objects.",
            "Practice 4+3 together.",
            "Ask one addition fact whose sum is 10 or less.",
        ],
        observation="Use the last try as the diagnostic.",
    )

    growth_plan = _plan(growth_target_code="growth.persistence")
    good_time = _draft(
        learn_minutes=8,
        do_minutes=6,
        grow_minutes=4,
        duration=18,
        learn_steps=[
            "Ask 3+2.",
            "Ask 4+4.",
            "Ask one fresh fact independently.",
        ],
        do_steps=["Walk to another room and try one more addition fact."],
        grow_steps=["After a miss, wait, then invite one more academic try."],
    )
    bad_time = _draft(
        learn_minutes=5,
        do_minutes=12,
        grow_minutes=5,
        duration=22,
        learn_steps=["Ask 3+4 once."],
        do_title="Soccer persistence game",
        do_steps=[
            "Roll a soccer ball back and forth to practice persistence.",
            "Keep the ball moving for most of the time.",
        ],
        grow_steps=["Talk about not giving up on the soccer ball."],
    )

    good_canonical = _draft(
        learn_steps=[
            "PRACTICE: try 2+2 with help if needed.",
            "PRACTICE: try 3+3.",
            "WHAT TO CHECK: one independent fact.",
        ],
        do_steps=["Stretch, then sit for the check already named above."],
        observation="WHAT TO CHECK: the independent fact in LEARN.",
    )
    bad_ambiguous = _draft(
        learn_title="Final check",
        learn_steps=["Do the final check on this inference."],
        do_title="Final mission",
        do_steps=["Now the final mission: test this one too."],
        observation="Also use the final test in DO.",
        primary_skill_code="reading.comprehension.simple_inference",
    )
    inference_plan = _plan(
        primary_skill_code="reading.comprehension.simple_inference",
        instruction_mode="practice",
        assessment_probe={
            "target_skill_code": "reading.comprehension.simple_inference",
            "observable_task": (
                "Ask what the character will do next from 1-2 sentences."
            ),
            "expected_outcome": "Child names a supported next action.",
        },
    )

    review_plan = _plan(instruction_mode="review")
    good_review = _draft(
        learn_steps=[
            "Retrieve 2+3 from last time.",
            "Try a variation: 3+4.",
            "Independent check: 5+2.",
        ],
        do_steps=["Move to a new spot and keep the same addition work."],
        observation="WHAT TO CHECK: independent 5+2, not the practice facts.",
    )
    bad_review = _draft(
        learn_minutes=8,
        do_minutes=6,
        grow_minutes=4,
        duration=18,
        learn_steps=["Ask 6+3 once as the whole review."],
        do_steps=["Stand nearby."],
        observation="That single item is the review.",
    )

    good_one_probe = _draft(
        learn_steps=[
            "Ask one addition fact whose sum is 10 or less.",
            "PRACTICE only after: show counting if needed.",
        ],
        observation="WHAT TO CHECK: the first probe, not later practice.",
    )
    bad_second_test = _draft(
        learn_steps=[
            "Ask one addition fact whose sum is 10 or less.",
            "Teach 5+2.",
        ],
        do_title="Final test",
        do_steps=["Now the final test on a new fact."],
        observation="Report whichever final check went better.",
    )

    good_overlay = _draft(
        learn_steps=[
            "Ask 2+5.",
            "Ask 4+3.",
            "Independent check: 6+1.",
        ],
        do_steps=["Keep addition going while walking to get paper."],
        grow_steps=["After a hard fact, pause, then try one more sum."],
        supporting=["growth.persistence"],
    )
    bad_overlay = _draft(
        learn_minutes=8,
        do_minutes=6,
        grow_minutes=4,
        learn_steps=["Ask 3+3.", "Ask 4+2."],
        do_title="Soccer rec game",
        do_steps=["Dribble a soccer ball to the goalie for persistence."],
        grow_steps=["Cheer the soccer race."],
        supporting=["growth.persistence"],
    )

    return (
        RendererContractCase(
            "case1_good_three_step_cues",
            "good",
            good_three,
            three_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case1_bad_vague_three_step",
            "bad",
            bad_three,
            three_plan,
            THREE_CONCRETE_CUES,
            None,
        ),
        RendererContractCase(
            "case2_good_fresh_item",
            "good",
            good_fresh,
            item_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case2_bad_practiced_item",
            "bad",
            bad_fresh,
            item_plan,
            FRESH_ASSESSMENT_ITEM,
            None,
        ),
        RendererContractCase(
            "case3_good_diagnostic_first",
            "good",
            good_diagnostic,
            diagnostic_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case3_bad_diagnostic_after_practice",
            "bad",
            bad_diagnostic,
            diagnostic_plan,
            DIAGNOSTIC_PROBE_BEFORE_TEACHING,
            None,
        ),
        RendererContractCase(
            "case4_good_academic_time_majority",
            "good",
            good_time,
            growth_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case4_bad_growth_steals_time",
            "bad",
            bad_time,
            growth_plan,
            PRIMARY_SKILL_TIME_MAJORITY,
            GROWTH_OVERLAY_DISCONNECTED,
        ),
        RendererContractCase(
            "case5_good_one_canonical",
            "good",
            good_canonical,
            inference_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case5_bad_ambiguous_finals",
            "bad",
            bad_ambiguous,
            inference_plan,
            ONE_CANONICAL_ASSESSMENT,
            None,
        ),
        RendererContractCase(
            "case6_good_review_practice",
            "good",
            good_review,
            review_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case6_bad_review_too_thin",
            "bad",
            bad_review,
            review_plan,
            REVIEW_PRACTICE_THEN_CHECK,
            SECTION_DURATION_IMPLAUSIBLE,
        ),
        RendererContractCase(
            "case7_good_one_diagnostic_measurement",
            "good",
            good_one_probe,
            diagnostic_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case7_bad_second_diagnostic_test",
            "bad",
            bad_second_test,
            diagnostic_plan,
            ONE_CANONICAL_ASSESSMENT,
            None,
        ),
        RendererContractCase(
            "case8_good_integrated_growth",
            "good",
            good_overlay,
            growth_plan,
            None,
            None,
        ),
        RendererContractCase(
            "case8_bad_disconnected_growth",
            "bad",
            bad_overlay,
            growth_plan,
            None,
            GROWTH_OVERLAY_DISCONNECTED,
        ),
        RendererContractCase(
            "age_respectful_good_mission",
            "good",
            _draft(
                learn_steps=[
                    "Show one CVC word on a scorecard.",
                    "Invite one independent encode.",
                ],
                learn_title="Mission check",
                do_title="Field challenge",
                do_steps=["Walk the hallway and tap three doorframes as checkpoints."],
                observation="Whether the child encodes the CVC word independently.",
                primary_skill_code="writing.spelling.cvc",
            ).model_copy(
                update={
                    "title": "Scorecard mission",
                    "parent_briefing": (
                        valid_daily_win_draft().parent_briefing.model_copy(
                            update={
                                "purpose": "Check one CVC encoding.",
                                "how_to_coach": "Wait. Offer one hint only if stuck.",
                            }
                        )
                    ),
                }
            ),
            _plan(
                primary_skill_code="writing.spelling.cvc",
                instruction_mode="foundation_review",
                presentation_constraint="age_respectful_foundation",
            ),
            None,
            None,
        ),
        RendererContractCase(
            "age_respectful_bad_baby_animals",
            "bad",
            _draft(
                learn_steps=[
                    "Look at the baby animals.",
                    "Good job, little reader!",
                ],
                learn_title="Little reader time",
                observation="Whether the child sounds out a kindergarten word.",
                primary_skill_code="writing.spelling.cvc",
            ).model_copy(
                update={
                    "title": "Baby animal sounds",
                    "parent_briefing": (
                        valid_daily_win_draft().parent_briefing.model_copy(
                            update={
                                "purpose": (
                                    "A kindergarten sounding-out game for "
                                    "little readers."
                                ),
                                "how_to_coach": "Cheer like they are a toddler.",
                            }
                        )
                    ),
                }
            ),
            _plan(
                primary_skill_code="writing.spelling.cvc",
                instruction_mode="foundation_review",
                presentation_constraint="age_respectful_foundation",
            ),
            AGE_RESPECTFUL_FOUNDATION,
            None,
        ),
    )
