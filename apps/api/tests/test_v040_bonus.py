from daily_win_api.domains.learning.bonus import (
    BONUS_CATALOG,
    bonus_is_not_academic,
    choose_bonus,
    low_engagement_categories_from_payloads,
)
from daily_win_api.domains.learning.observations import OBSERVATION_BONUS_ENGAGEMENT
from daily_win_api.domains.learning.projects import next_project_beat
from daily_win_api.domains.learning.school_context import ParentReportedSchoolContext


def test_bonus_is_optional_and_not_mastery() -> None:
    bonus = choose_bonus(
        primary_skill_code="math.addition.within_10",
        teach_the_coach=False,
        age_years=9,
    )
    assert bonus.optional is True
    assert bonus.counts_as_mastery is False
    assert bonus_is_not_academic(bonus.code)
    assert bonus.safety
    assert all(item["minutes"] <= 5 for item in BONUS_CATALOG)


def test_engagement_avoids_repeated_low_mechanic() -> None:
    bonus = choose_bonus(
        primary_skill_code="math.addition.within_10",
        teach_the_coach=False,
        low_engagement_categories=("memory",),
        age_years=9,
    )
    assert bonus.category != "memory"


def test_repeated_not_into_it_becomes_low_engagement_categories() -> None:
    avoided = low_engagement_categories_from_payloads(
        (
            {
                "observation_type": OBSERVATION_BONUS_ENGAGEMENT,
                "signal": "not_into_it",
                "category": "physical",
            },
            {
                "observation_type": OBSERVATION_BONUS_ENGAGEMENT,
                "signal": "not_into_it",
                "category": "physical",
            },
            {
                "observation_type": OBSERVATION_BONUS_ENGAGEMENT,
                "signal": "loved_it",
                "category": "memory",
            },
        )
    )
    assert avoided == ("physical",)


def test_school_context_is_not_measurement() -> None:
    payload = ParentReportedSchoolContext(teacher_focus="spelling endings")
    assert payload.as_dict()["counts_as_measurement"] is False
    assert payload.epistemic_kind == "PROFILE_REPORT"


def test_project_memory_is_bounded() -> None:
    first = next_project_beat(None, None)
    assert first is not None
    second = next_project_beat(first.project_code, first.beat)
    assert second is not None
    assert second.beat != first.beat
    assert "narrative" not in second.as_dict()
