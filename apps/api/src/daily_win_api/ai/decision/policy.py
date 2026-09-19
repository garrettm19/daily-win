from enum import StrEnum

from daily_win_api.ai.decision import VerificationResult

# Uncalibrated starting values. Must be revised with labelled eval data.
HIGH_CONFIDENCE = 0.8


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


def combine_verification(
    result: VerificationResult, *, high: float = HIGH_CONFIDENCE
) -> Verdict:
    safety_fail = [
        item
        for item in result.decisions
        if item.safety_critical and item.value is True and item.confidence >= high
    ]
    if safety_fail:
        return Verdict.FAIL
    uncertain_safety = [
        item
        for item in result.decisions
        if item.safety_critical and item.confidence < high
    ]
    if uncertain_safety:
        return Verdict.UNCERTAIN
    high_fail = [
        item
        for item in result.decisions
        if not item.safety_critical
        and item.name != "substantially_repeats_recent_activity"
        and item.value is False
        and item.confidence >= high
    ]
    repeats = next(
        (
            item
            for item in result.decisions
            if item.name == "substantially_repeats_recent_activity"
        ),
        None,
    )
    if repeats is not None and repeats.value is True and repeats.confidence >= high:
        return Verdict.FAIL
    if high_fail:
        return Verdict.FAIL
    low = [item for item in result.decisions if item.confidence < high]
    if low:
        return Verdict.UNCERTAIN
    return Verdict.PASS
