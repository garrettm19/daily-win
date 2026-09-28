"""Smart, plan-derived reflection prompts. Keep reflection under about one minute."""

from daily_win_api.domains.learning.enums import InstructionMode
from daily_win_api.domains.learning.taxonomy import is_academic_code


def smart_reflection_fields(
    *,
    instruction_mode: str,
    skill_code: str,
    asks_about_setback: bool,
    teach_the_coach: bool,
) -> dict[str, object]:
    academic = is_academic_code(skill_code)
    questions: list[dict[str, str]] = []
    if academic:
        if instruction_mode == InstructionMode.DIAGNOSTIC.value:
            questions.append(
                {
                    "id": "academic_result",
                    "prompt": "How independently did they complete the check?",
                }
            )
        elif skill_code.startswith("writing."):
            questions.append(
                {
                    "id": "self_correction",
                    "prompt": "Did they notice and fix the target error themselves?",
                }
            )
        else:
            questions.append(
                {
                    "id": "academic_result",
                    "prompt": "How independently did they solve the measured part?",
                }
            )
        questions.append(
            {
                "id": "performance_effort",
                "prompt": "Did this look automatic, or effortful?",
            }
        )
        questions.append(
            {
                "id": "strategy",
                "prompt": "What strategy did you actually see?",
            }
        )
    if asks_about_setback:
        questions.append(
            {
                "id": "setback_response",
                "prompt": "What happened after the first setback?",
            }
        )
    questions.append(
        {
            "id": "notice_chips",
            "prompt": "Anything you noticed? (optional)",
        }
    )
    questions.append(
        {
            "id": "bonus_engagement",
            "prompt": "If you tried the bonus, how into it were they?",
        }
    )
    return {
        "questions": questions[:5],
        "notice_chips": _notice_chips(skill_code, teach_the_coach),
        "strategy_options": _strategy_options(skill_code),
        "self_correction_options": (
            "self_corrected",
            "corrected_after_prompt",
            "did_not_correct",
            "not_observed",
        ),
        "effort_options": (
            "automatic",
            "effortful_but_independent",
            "effortful_with_support",
            "not_observed",
        ),
        "bonus_engagement_options": (
            "loved_it",
            "liked_it",
            "neutral",
            "not_into_it",
            "skipped",
        ),
    }


def _notice_chips(skill_code: str, teach_the_coach: bool) -> tuple[str, ...]:
    chips = [
        "self-corrected",
        "explained reasoning",
        "worked automatically",
        "used a strategy",
        "asked for help",
        "got frustrated",
        "kept trying",
        "lost interest",
    ]
    if teach_the_coach:
        chips.insert(1, "taught the coach")
    if skill_code.startswith("writing."):
        chips.append("non-target error noticed")
    return tuple(chips)


def _strategy_options(skill_code: str) -> tuple[str, ...]:
    if skill_code.startswith("math."):
        return (
            "mental_automatic",
            "counted",
            "drew_modelled",
            "decomposed_numbers",
            "needed_help",
            "guessed_unclear",
            "not_observed",
        )
    if skill_code.startswith("reading."):
        return (
            "sounded_out",
            "reread",
            "used_context",
            "recalled_directly",
            "needed_prompt",
            "not_observed",
        )
    if skill_code.startswith("writing."):
        return (
            "sounded_out",
            "used_known_pattern",
            "reread_own_work",
            "self_corrected",
            "needed_a_model",
            "not_observed",
        )
    return ("not_observed",)
