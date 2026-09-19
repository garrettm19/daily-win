import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from daily_win_api.ai.schemas import (
    DailyWinDraft,
    DailyWinGenerationResult,
    SegmentType,
)
from daily_win_api.domains.daily_wins.safety import validate_daily_win_safety
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError
from daily_win_api.eval.fixtures import EvalFixture
from daily_win_api.eval.pricing import estimate_cost_usd

HUMAN_RUBRIC_KEYS = (
    "age_appropriateness",
    "educational_usefulness",
    "personalization",
    "clarity_for_parent",
    "activity_coherence",
    "fun_engagement",
    "adaptation_quality",
    "novelty",
    "physical_safety",
    "overall_usefulness",
)

_CAREGIVER_TERMS = re.compile(
    r"\b(?:dad|mom|mother|father|mommy|daddy)\b", re.IGNORECASE
)
_PRONOUNS = re.compile(r"\b(?:he|him|his|she|her|hers)\b", re.IGNORECASE)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str | None = None


@dataclass
class FixtureEvalResult:
    fixture_id: str
    model: str
    provider: str
    checks: list[CheckResult]
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    context_chars: int
    human_rubric: dict[str, int | None] = field(
        default_factory=lambda: dict.fromkeys(HUMAN_RUBRIC_KEYS)
    )
    error: str | None = None

    @property
    def all_automated_passed(self) -> bool:
        return self.error is None and all(item.passed for item in self.checks)


def score_generation(
    fixture: EvalFixture, result: DailyWinGenerationResult
) -> FixtureEvalResult:
    context = fixture.context
    draft = result.draft
    blob = _draft_blob(draft)
    checks = [
        _check("schema_validity", True),
        _check(
            "instruction_plan_alignment",
            draft.primary_skill_code == context.instruction_plan.primary_skill_code,
            draft.primary_skill_code,
        ),
        _check(
            "valid_skill_codes",
            _skills_allowed(draft, context.allowed_skill_codes),
        ),
        _check(
            "material_allowlist",
            all(
                material.value in context.allowed_materials
                for material in draft.materials
            ),
        ),
        _check(
            "duration",
            10 <= draft.duration_minutes <= 25,
            str(draft.duration_minutes),
        ),
        _check(
            "learn_do_grow",
            [segment.type for segment in draft.segments]
            == [SegmentType.LEARN, SegmentType.DO, SegmentType.GROW],
        ),
        _safety_check(draft),
        _check(
            "adaptation_summary_when_required",
            _adaptation_summary_ok(fixture, draft),
        ),
        _check(
            "no_caregiver_assumption",
            _no_unwarranted_caregiver(
                blob, context.parent_reported_baseline.motivators
            ),
        ),
        _check("no_inferred_pronouns", _PRONOUNS.search(blob) is None),
        _check(
            "no_repeated_recent_theme",
            _theme_not_repeated(draft, context.recent_themes),
        ),
        _check(
            "context_size_bounded",
            len(context.bounded_evidence_summaries) <= 6
            and len(context.recent_themes) <= 3,
        ),
    ]
    return FixtureEvalResult(
        fixture_id=fixture.id,
        model=result.model,
        provider=result.provider,
        checks=checks,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        estimated_cost_usd=estimate_cost_usd(
            result.model, result.input_tokens, result.output_tokens
        ),
        context_chars=len(context.model_dump_json()),
    )


def score_invalid_payload(
    fixture: EvalFixture, *, model: str, provider: str, error: str
) -> FixtureEvalResult:
    return FixtureEvalResult(
        fixture_id=fixture.id,
        model=model,
        provider=provider,
        checks=[_check("schema_validity", False, error)],
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        estimated_cost_usd=None,
        context_chars=len(fixture.context.model_dump_json()),
        error=error,
    )


def empty_human_rubric() -> dict[str, None]:
    return dict.fromkeys(HUMAN_RUBRIC_KEYS)


def write_results(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def result_to_dict(item: FixtureEvalResult) -> dict[str, Any]:
    data = asdict(item)
    return data


def validate_draft_or_error(payload: object) -> DailyWinDraft | str:
    try:
        return DailyWinDraft.model_validate(payload)
    except ValidationError as exc:
        return f"schema_validation_failed:{exc.error_count()}"


def _check(name: str, passed: bool, detail: str | None = None) -> CheckResult:
    return CheckResult(name=name, passed=passed, detail=detail)


def _safety_check(draft: DailyWinDraft) -> CheckResult:
    try:
        validate_daily_win_safety(draft)
    except SafetyRejectedError as exc:
        return _check("deterministic_safety", False, exc.rule)
    return _check("deterministic_safety", True)


def _skills_allowed(draft: DailyWinDraft, allowed: list[str]) -> bool:
    codes = [draft.primary_skill_code, *draft.supporting_skill_codes]
    return all(code in allowed for code in codes)


def _adaptation_summary_ok(fixture: EvalFixture, draft: DailyWinDraft) -> bool:
    required = fixture.win_kind == "adaptive"
    if required:
        return bool(draft.adaptation_summary)
    return True


def _no_unwarranted_caregiver(blob: str, motivators: list[str]) -> bool:
    context_text = " ".join(motivators).lower()
    for match in _CAREGIVER_TERMS.finditer(blob):
        term = match.group(0).lower()
        if term not in context_text:
            return False
    return True


def _theme_not_repeated(draft: DailyWinDraft, recent_themes: list[str]) -> bool:
    if not recent_themes:
        return True
    title = draft.title.strip().lower()
    return all(title != prior.strip().lower() for prior in recent_themes)


def _draft_blob(draft: DailyWinDraft) -> str:
    parts = [
        draft.title,
        draft.objective,
        draft.personalization_summary,
        draft.observation_focus,
        draft.parent_briefing.purpose,
        draft.parent_briefing.how_to_coach,
        draft.adaptations.if_too_easy,
        draft.adaptations.if_too_hard,
        *draft.success_checks,
        *(material.value for material in draft.materials),
    ]
    for segment in draft.segments:
        parts.append(segment.title)
        parts.append(segment.parent_role)
        parts.extend(segment.steps)
    return " ".join(parts)
