from datetime import UTC, datetime

from daily_win_api.domains.learning.academic import EVENT_TYPE_SKILL_ASSESSMENT
from daily_win_api.domains.learning.enums import EvidenceKind
from daily_win_api.domains.learning.observations import (
    OBSERVATION_EFFORT,
    OBSERVATION_SELF_CORRECTION,
    OBSERVATION_STRATEGY,
    observation_payload,
)
from daily_win_api.domains.learning.weekly import (
    SessionEvidence,
    emerging_need_signals,
    synthesize_week,
    weekly_text_is_safe,
)
from daily_win_api.eval.coaching import (
    _case_contradictory,
    _case_dislikes_mechanic,
    _case_math_strong_writing_weak,
    coaching_errors,
)

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_weekly_report_is_evidence_grounded() -> None:
    summary = synthesize_week(
        _case_math_strong_writing_weak(), week_start=NOW, week_end=NOW
    )
    blob = " ".join(summary.what_looked_strong + summary.what_still_took_work).lower()
    assert "math" in blob
    assert "writing" in blob
    assert weekly_text_is_safe(blob)
    assert summary.claims_trace
    assert all(item[0] for item in summary.claims_trace)


def test_weekly_report_stays_cautious_on_contradiction() -> None:
    summary = synthesize_week(_case_contradictory(), week_start=NOW, week_end=NOW)
    blob = " ".join(summary.what_looked_strong + summary.what_still_took_work).lower()
    assert "gifted" not in blob
    assert "math kid" not in blob


def test_engagement_does_not_override_mastery() -> None:
    summary = synthesize_week(_case_dislikes_mechanic(), week_start=NOW, week_end=NOW)
    assert "physical" in summary.engagement_memory.low_engagement_categories
    assert summary.wins_completed == 2


def test_emerging_need_is_advisory_only() -> None:
    sessions = tuple(
        SessionEvidence(
            skill_code="writing.organization.sequence",
            instruction_mode="practice",
            academic_result="correct_independently",
            non_target_error="writing.spelling.endings_suffixes",
            source_keys=(f"n{index}",),
        )
        for index in range(3)
    )
    signals = emerging_need_signals(sessions)
    assert signals
    assert signals[0].recommendation == "consider_diagnostic"
    assert "weak" not in signals[0].claim.lower()


def test_self_correction_is_observation_not_measurement() -> None:
    payload = observation_payload(OBSERVATION_SELF_CORRECTION, "self_corrected")
    assert payload["epistemic_kind"] == "OBSERVATION"
    assert payload["reporting_kind"] == "parent_reported"
    assert EVENT_TYPE_SKILL_ASSESSMENT != "skill_observation"
    assert EvidenceKind.OBSERVATION.value == "OBSERVATION"
    effort = observation_payload(OBSERVATION_EFFORT, "automatic")
    strategy = observation_payload(OBSERVATION_STRATEGY, "counted")
    assert effort["epistemic_kind"] == strategy["epistemic_kind"] == "OBSERVATION"


def test_coaching_eval_suite_passes() -> None:
    assert coaching_errors() == []
