from daily_win_api.ai.prompts.current import PROMPT_VERSION, SYSTEM_PROMPT
from daily_win_api.ai.prompts.daily_win_v1 import (
    PROMPT_VERSION as V1_PROMPT_VERSION,
)
from daily_win_api.ai.prompts.daily_win_v2 import (
    PROMPT_VERSION as V2_PROMPT_VERSION,
)


def test_active_prompt_version_is_v3() -> None:
    assert PROMPT_VERSION == "daily_win_generator_v3"
    assert V1_PROMPT_VERSION == "daily_win_generator_v1"
    assert V2_PROMPT_VERSION == "daily_win_generator_v2"


def test_prompt_requires_skimmable_parent_briefing() -> None:
    text = SYSTEM_PROMPT.lower()
    assert "30-60 seconds" in text
    assert "purpose: maximum 2 concise sentences" in text
    assert "how_to_coach: maximum 3 concise prompts or instructions" in text
    assert "watch_for: maximum 2 sentences" in text
    assert "avoid: maximum 2 sentences" in text


def test_prompt_contains_caregiver_and_pronoun_constraints() -> None:
    assert (
        "Do not assume caregiver relationship terms such as Dad, Mom, "
        "mother, or father."
    ) in SYSTEM_PROMPT
    assert 'Address the caregiver as "you"' in SYSTEM_PROMPT
    assert "Do not infer the child's pronouns." in SYSTEM_PROMPT
    assert "Prefer the child's nickname or a neutral sentence construction." in (
        SYSTEM_PROMPT
    )


def test_prompt_requires_academic_learn_and_one_theme() -> None:
    text = SYSTEM_PROMPT.lower()
    assert "must not be merely generic planning" in text
    assert "one coherent theme" in text
    assert "unnecessary scripts" in text
    assert "math, reading, or writing" in text


def test_v3_prompt_does_not_overstate_evidence() -> None:
    text = SYSTEM_PROMPT
    assert "Use the supplied AdaptationDirective." in text
    assert "Do not infer more than the evidence supports." in text
    assert "meaningful but modest adjustment" in text
    assert "Do not merely repeat the prior activity with different nouns." in text
    assert "Hayes has strong persistence now." in text
    assert "Not acceptable:" in text
    assert "permanent trait" in text
