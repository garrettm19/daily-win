import pytest

from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.domains.daily_wins.safety import (
    CHEMICAL,
    CHOKING_HAZARD,
    FIRE_OR_HEAT,
    HEAVY_LIFTING,
    JUMPING_FROM_HEIGHT,
    MEDICATION,
    ROAD_OR_TRAFFIC,
    SHARP_OBJECT,
    UNSAFE_CLIMBING,
    validate_daily_win_safety,
)
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError


def _draft_with_step(step: str):
    return valid_daily_win_draft(extra_step=step, safety_flags=[])


@pytest.mark.parametrize(
    "step",
    [
        "Jump three times on the floor.",
        "Run to a marker and back.",
        "Kick a soft ball.",
        "Gently toss a soft ball.",
        "Lift a plastic cup.",
        "Stack blocks.",
        "Build a block tower.",
        "Walk across the room.",
        "Try again after a miss.",
        "Do not jump in with the answer.",
        "Stand up from a chair and walk to the marker.",
    ],
)
def test_ordinary_child_activities_are_safe(step: str) -> None:
    validate_daily_win_safety(_draft_with_step(step))


@pytest.mark.parametrize(
    ("step", "rule"),
    [
        ("Jump off a chair.", JUMPING_FROM_HEIGHT),
        ("Jump from a table.", JUMPING_FROM_HEIGHT),
        ("Climb onto the counter.", UNSAFE_CLIMBING),
        ("Climb a bookshelf.", UNSAFE_CLIMBING),
        ("Cross the road.", ROAD_OR_TRAFFIC),
        ("Play near traffic.", ROAD_OR_TRAFFIC),
        ("Use a knife.", SHARP_OBJECT),
        ("Use scissors.", SHARP_OBJECT),
        ("Light a candle.", FIRE_OR_HEAT),
        ("Use the stove or oven.", FIRE_OR_HEAT),
        ("Light a match.", FIRE_OR_HEAT),
        ("Strike a match.", FIRE_OR_HEAT),
        ("Use matches to start a fire.", FIRE_OR_HEAT),
        ("Play with matches.", FIRE_OR_HEAT),
        ("Hand the child a box of matches.", FIRE_OR_HEAT),
        ("Do not give them matchsticks.", FIRE_OR_HEAT),
        ("Lift a heavy object.", HEAVY_LIFTING),
        ("Take medication.", MEDICATION),
        ("Use cleaning chemicals.", CHEMICAL),
        ("Offer marbles as a prize.", CHOKING_HAZARD),
    ],
)
def test_hazardous_instructions_are_rejected(step: str, rule: str) -> None:
    with pytest.raises(SafetyRejectedError) as caught:
        validate_daily_win_safety(_draft_with_step(step))
    assert caught.value.code == "unsafe_content"
    assert caught.value.rule == rule


def test_avoid_field_warning_does_not_false_positive() -> None:
    draft = valid_daily_win_draft(safety_flags=[])
    draft = draft.model_copy(
        update={
            "parent_briefing": draft.parent_briefing.model_copy(
                update={
                    "avoid": (
                        "Do not use scissors, climb onto counters, or cross the road."
                    )
                }
            )
        }
    )
    validate_daily_win_safety(draft)


def test_ordinary_match_verbs_are_not_fire_hazards() -> None:
    for step in (
        "the inference matches the clues",
        "match each word to its meaning",
        "find the matching picture",
        "see whether your answer matches",
    ):
        validate_daily_win_safety(_draft_with_step(step))


def test_substring_inside_another_word_does_not_match() -> None:
    validate_daily_win_safety(_draft_with_step("Keep repeating the rebuild."))
    validate_daily_win_safety(_draft_with_step("Use the sidewalk chalk indoors."))
    validate_daily_win_safety(
        _draft_with_step("Celebrate one specific effort after the miss.")
    )
