from dataclasses import dataclass

from daily_win_api.domains.learning.academic import project_academic_band
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.eval.builders import EVAL_NOW, evidence

R = AcademicResult
B = AcademicBand


@dataclass(frozen=True)
class LearnerCase:
    id: str
    label: str
    days_and_results: tuple[tuple[int, AcademicResult, str], ...]
    expected_band: AcademicBand
    expected_remediation: bool
    forbid_bands: tuple[AcademicBand, ...] = ()


def learner_state_cases() -> tuple[LearnerCase, ...]:
    return (
        LearnerCase(
            "case_a_step_incorrect",
            "Incorrect only is emerging",
            ((0, R.INCORRECT, "s1"),),
            B.EMERGING,
            False,
            forbid_bands=(B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "case_a_step_light_prompt",
            "Incorrect then light prompt is developing",
            ((0, R.INCORRECT, "s1"), (1, R.CORRECT_AFTER_LIGHT_PROMPT, "s2")),
            B.DEVELOPING,
            False,
            forbid_bands=(B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "case_a_step_independent",
            "First independent is still developing",
            (
                (0, R.INCORRECT, "s1"),
                (1, R.CORRECT_AFTER_LIGHT_PROMPT, "s2"),
                (2, R.CORRECT_INDEPENDENTLY, "s3"),
            ),
            B.DEVELOPING,
            False,
            forbid_bands=(B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "case_a_spaced_independent",
            "Spaced second independent is retained",
            (
                (0, R.INCORRECT, "s1"),
                (1, R.CORRECT_AFTER_LIGHT_PROMPT, "s2"),
                (2, R.CORRECT_INDEPENDENTLY, "s3"),
                (10, R.CORRECT_INDEPENDENTLY, "s4"),
            ),
            B.RETAINED,
            False,
        ),
        LearnerCase(
            "case_b_two_independent_same_day_same_session",
            "Two independent results in one session are not retained",
            (
                (0, R.CORRECT_INDEPENDENTLY, "same"),
                (0, R.CORRECT_INDEPENDENTLY, "same"),
            ),
            B.DEVELOPING,
            False,
            forbid_bands=(B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "case_b_two_independent_same_day_two_sessions",
            "Two same-day sessions can demonstrate but not retain",
            (
                (0, R.CORRECT_INDEPENDENTLY, "am"),
                (0, R.CORRECT_INDEPENDENTLY, "pm"),
            ),
            B.DEMONSTRATED,
            False,
            forbid_bands=(B.RETAINED,),
        ),
        LearnerCase(
            "case_c_retained_then_weak",
            "Retained then repeated weak evidence needs remediation",
            (
                (0, R.CORRECT_INDEPENDENTLY, "s1"),
                (8, R.CORRECT_INDEPENDENTLY, "s2"),
                (12, R.INCORRECT, "s3"),
                (13, R.CORRECT_AFTER_SIGNIFICANT_HELP, "s4"),
            ),
            B.DEVELOPING,
            True,
            forbid_bands=(B.RETAINED,),
        ),
        LearnerCase(
            "case_d_lucky_independent_among_incorrect",
            "One independent among later incorrects does not stay retained",
            (
                (0, R.INCORRECT, "s1"),
                (1, R.INCORRECT, "s2"),
                (2, R.CORRECT_INDEPENDENTLY, "s3"),
                (3, R.INCORRECT, "s4"),
                (4, R.INCORRECT, "s5"),
            ),
            B.DEVELOPING,
            True,
            forbid_bands=(B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "significant_help_only",
            "Only significant help is emerging",
            ((0, R.CORRECT_AFTER_SIGNIFICANT_HELP, "s1"),),
            B.EMERGING,
            False,
            forbid_bands=(B.DEVELOPING, B.DEMONSTRATED, B.RETAINED),
        ),
        LearnerCase(
            "not_attempted_ignored",
            "Skipped attempts do not create a band",
            ((0, R.NOT_ATTEMPTED, "s1"),),
            B.NOT_OBSERVED,
            False,
        ),
        LearnerCase(
            "empty_evidence",
            "No evidence is not_observed",
            (),
            B.NOT_OBSERVED,
            False,
        ),
        LearnerCase(
            "two_independent_six_days_not_retained",
            "Independent successes 6 days apart are demonstrated not retained",
            (
                (0, R.CORRECT_INDEPENDENTLY, "s1"),
                (6, R.CORRECT_INDEPENDENTLY, "s2"),
            ),
            B.DEMONSTRATED,
            False,
            forbid_bands=(B.RETAINED,),
        ),
    )


def evaluate_learner_case(case: LearnerCase) -> list[str]:
    last_day = max((day for day, _result, _session in case.days_and_results), default=0)
    items = [
        evidence(result, day=day - last_day, session=session)
        for day, result, session in case.days_and_results
    ]
    snap = project_academic_band(items, now=EVAL_NOW)
    errors: list[str] = []
    if snap.band is not case.expected_band:
        errors.append(f"band {snap.band} != {case.expected_band}")
    if snap.needs_remediation is not case.expected_remediation:
        errors.append(
            f"remediation {snap.needs_remediation} != {case.expected_remediation}"
        )
    if snap.band in case.forbid_bands:
        errors.append(f"forbidden band {snap.band}")
    return errors
