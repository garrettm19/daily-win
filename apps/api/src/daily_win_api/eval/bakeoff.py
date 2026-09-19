"""Fair Terra vs Luna renderer bakeoff. Does not change the production default."""

from __future__ import annotations

import hashlib
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from daily_win_api.ai.exceptions import ModelGatewayError, ModelGatewaySchemaError
from daily_win_api.ai.gateway import build_model_gateway
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.ai.schemas import DailyWinDraft, DailyWinGenerationResult
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, Settings, get_settings
from daily_win_api.domains.daily_wins.safety import validate_daily_win_safety
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError
from daily_win_api.eval.attribution import FailureOwner, owner_for_error
from daily_win_api.eval.bakeoff_cases import BakeoffCase, load_bakeoff_cases
from daily_win_api.eval.human_review import review_score_template
from daily_win_api.eval.pricing import (
    estimate_cost_parts,
    estimate_cost_usd,
    pricing_catalog,
)
from daily_win_api.eval.renderer_quality import parent_burden
from daily_win_api.eval.scoring import write_results

TERRA = "gpt-5.6-terra"
LUNA = "gpt-5.6-luna"
BAKEOFF_MODELS = (TERRA, LUNA)
BLIND_SALT = "daily-win-v034-blind"
WEEKS_PER_MONTH = 52 / 12
MAX_ATTEMPTS = 2
RETRYABLE_CODES = frozenset(
    {
        "provider_timeout",
        "provider_connection_error",
        "provider_server_error",
        "rate_limited",
        "schema_validation_failed",
    }
)
PRIVACY_NEEDLES = (
    "child_id",
    "household_id",
    "instruction_plan_id",
    "baseline_id",
    "session_secret",
    "session_key",
    "sk-proj",
    "sk-",
    "password",
    "authorization",
)
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "then",
        "this",
        "that",
        "from",
        "after",
        "ask",
        "child",
        "parent",
        "invite",
        "once",
        "them",
        "they",
        "their",
        "into",
        "onto",
        "each",
        "have",
        "does",
        "using",
        "about",
        "without",
    }
)
BAKEOFF_HUMAN_KEYS = (
    "educational_usefulness",
    "plan_fidelity",
    "age_appropriateness",
    "parent_clarity",
    "engagement",
    "assessment_quality",
    "coaching_quality",
    "overall",
)
_MODE_HINTS = {
    "introduce": ("first", "new", "show", "model", "introduce", "together"),
    "practice": ("practice", "another", "keep", "again"),
    "review": ("review", "remember", "revisit", "again", "recall"),
    "remediation": (
        "slower",
        "together",
        "rebuild",
        "support",
        "smaller",
        "help",
    ),
    "diagnostic": (
        "check",
        "whether",
        "find out",
        "quick",
        "see if",
        "independent",
    ),
}


class _Gateway(Protocol):
    def generate_daily_win(self, context: Any) -> DailyWinGenerationResult: ...


@dataclass
class CallRecord:
    model: str
    attempts: int
    retried: bool
    retry_reason: str | None
    error: str | None
    prompt_version: str
    schema_valid: bool
    target_skill_fidelity: bool | None
    assessment_probe_fidelity: bool | None
    scaffold_fidelity: bool | None
    instruction_mode_fidelity: bool | None
    duration_valid: bool | None
    material_allowlist_valid: bool | None
    deterministic_safety: bool | None
    parent_burden: dict[str, Any] | None
    theme_repetition: bool | None
    hard_failures: list[str]
    model_quality_hard_failures: list[str]
    failure_owner: str | None
    production_would_reject: bool | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: float | None
    cost_breakdown: dict[str, float] | None = None
    draft: dict[str, Any] | None = None


@dataclass(frozen=True)
class BlindAssignment:
    case_id: str
    a_model: str
    b_model: str


def arm_assignment(case_id: str) -> BlindAssignment:
    digest = hashlib.sha256(f"{BLIND_SALT}|{case_id}".encode()).digest()
    if digest[0] % 2 == 0:
        return BlindAssignment(case_id, TERRA, LUNA)
    return BlindAssignment(case_id, LUNA, TERRA)


def privacy_issues(payload: str) -> list[str]:
    lowered = payload.lower()
    issues = [needle for needle in PRIVACY_NEEDLES if needle in lowered]
    if _UUID.search(payload):
        issues.append("uuid")
    if _EMAIL.search(payload):
        issues.append("email")
    return issues


def empty_human_scores() -> dict[str, None]:
    return dict.fromkeys(BAKEOFF_HUMAN_KEYS)


def run_terra_luna_bakeoff(
    *,
    live: bool,
    settings: Settings | None = None,
    output_dir: Path | None = None,
    gateways: dict[str, _Gateway] | None = None,
) -> dict[str, Path]:
    cases = load_bakeoff_cases()
    resolved = gateways or _gateways(live=live, settings=settings)
    created_at = datetime.now(UTC)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    directory = output_dir or Path(__file__).resolve().parents[3] / "eval-results"

    case_rows: list[dict[str, Any]] = []
    call_rows: list[CallRecord] = []
    attempted = 0
    succeeded = 0
    retried = 0

    for case in cases:
        issues = privacy_issues(case.context.model_dump_json())
        if issues:
            raise SystemExit(
                f"Bakeoff context {case.id} failed privacy scan: {issues}"
            )
        outputs: dict[str, Any] = {}
        for model in BAKEOFF_MODELS:
            attempted += 1
            record = _call_once(resolved[model], case, model)
            if record.retried:
                retried += 1
                attempted += 1
            if record.error is None and record.schema_valid:
                succeeded += 1
            outputs[model] = asdict(record)
            call_rows.append(record)
            if live:
                time.sleep(0.25)
        case_rows.append(
            {
                "id": case.id,
                "coverage": case.coverage,
                "golden_id": case.golden_id,
                "profile_summary": case.profile_summary,
                "plan_summary": case.plan_summary,
                "instruction_plan": _plan_payload(case),
                "context_sha256": case.context_sha256,
                "privacy_ok": True,
                "synthetic": True,
                "store": False,
                "prompt_version": PROMPT_VERSION,
                "outputs": outputs,
            }
        )

    summary = _summarize(call_rows)
    payload = {
        "created_at": created_at.isoformat(),
        "live": live,
        "bakeoff": "terra-luna",
        "prompt_version": PROMPT_VERSION,
        "models": list(BAKEOFF_MODELS),
        "baseline_model": DEFAULT_OPENAI_MODEL,
        "production_default_unchanged": DEFAULT_OPENAI_MODEL == TERRA,
        "routing_implemented": False,
        "calls_attempted": attempted,
        "calls_succeeded": succeeded,
        "calls_retried": retried,
        "case_count": len(cases),
        "privacy": {
            "synthetic_only": True,
            "no_db_ids": True,
            "no_session_secrets": True,
            "no_real_parent_notes": True,
            "store": False,
        },
        "note": (
            "Eval results are operational comparison artifacts. They are not "
            "canonical learner memory and must not be written to PostgreSQL "
            "child tables. Human scores are review-only."
        ),
        "pricing": pricing_catalog(),
        "summary": summary,
        "recommendation": _recommend(summary, live=live),
        "cases": case_rows,
    }
    json_path = directory / f"{stamp}-terra-luna.json"
    review_path = directory / f"{stamp}-terra-luna-review.md"
    reveal_path = directory / f"{stamp}-terra-luna-reveal.json"
    write_results(json_path, payload)
    review_path.write_text(_review_markdown(cases, case_rows), encoding="utf-8")
    write_results(reveal_path, _reveal_payload(cases, stamp))
    return {"json": json_path, "review": review_path, "reveal": reveal_path}


def _gateways(*, live: bool, settings: Settings | None) -> dict[str, _Gateway]:
    if not live:
        return {
            TERRA: FakeModelGateway(model=TERRA),
            LUNA: FakeModelGateway(model=LUNA),
        }
    resolved = settings or get_settings()
    return {
        model: build_model_gateway(
            resolved.model_copy(update={"openai_model": model})
        )
        for model in BAKEOFF_MODELS
    }


def _call_once(gateway: _Gateway, case: BakeoffCase, model: str) -> CallRecord:
    last_error: str | None = None
    retry_reason: str | None = None
    generated: DailyWinGenerationResult | None = None
    attempts = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts = attempt
        try:
            generated = gateway.generate_daily_win(case.context)
            last_error = None
            break
        except (ModelGatewaySchemaError, ModelGatewayError) as exc:
            last_error = exc.code
            if attempt < MAX_ATTEMPTS and exc.code in RETRYABLE_CODES:
                retry_reason = exc.code
                continue
            break
    if generated is None:
        owner = owner_for_error(last_error)
        hard = (
            "schema_invalid"
            if last_error == "schema_validation_failed"
            else "provider_error"
        )
        return CallRecord(
            model=model,
            attempts=attempts,
            retried=retry_reason is not None,
            retry_reason=retry_reason,
            error=last_error,
            prompt_version=PROMPT_VERSION,
            schema_valid=False,
            target_skill_fidelity=None,
            assessment_probe_fidelity=None,
            scaffold_fidelity=None,
            instruction_mode_fidelity=None,
            duration_valid=None,
            material_allowlist_valid=None,
            deterministic_safety=None,
            parent_burden=None,
            theme_repetition=None,
            hard_failures=[hard],
            model_quality_hard_failures=(
                [hard] if owner is FailureOwner.SCHEMA_FAILURE else []
            ),
            failure_owner=None if owner is None else owner.value,
            production_would_reject=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            latency_ms=None,
            estimated_cost_usd=None,
        )
    return _score_call(
        case,
        generated,
        attempts=attempts,
        retry_reason=retry_reason,
    )


def _score_call(
    case: BakeoffCase,
    result: DailyWinGenerationResult,
    *,
    attempts: int,
    retry_reason: str | None,
) -> CallRecord:
    draft = result.draft
    plan = case.context.instruction_plan
    skill_ok = draft.primary_skill_code == plan.primary_skill_code
    probe_ok = _probe_fidelity(plan.assessment_probe, draft)
    scaffold_ok = _scaffold_fidelity(plan.scaffold_level, draft)
    mode_ok = _mode_fidelity(plan.instruction_mode, draft)
    duration_ok = _duration_valid(plan.duration_minutes, draft)
    materials_ok = all(
        material.value in case.context.allowed_materials
        for material in draft.materials
    )
    safety_ok = _safety_ok(draft)
    objective_ok = skill_ok and _objective_preserved(
        plan.assessment_objective, draft
    )
    burden = parent_burden(draft)
    theme_ok = _theme_not_repeated(draft, case.context.recent_themes)
    hard: list[str] = []
    if not skill_ok:
        hard.append("wrong_primary_skill")
    if not probe_ok:
        hard.append("probe_wrong_construct")
    if not scaffold_ok:
        hard.append("ignores_required_scaffold")
    if not safety_ok:
        hard.append("unsafe_content")
    if not duration_ok:
        hard.append("duration_unfit")
    if not materials_ok:
        hard.append("prohibited_materials")
    if not objective_ok:
        hard.append("changed_instructional_objective")
    owner = FailureOwner.MODEL_OUTPUT_FAILURE if hard else None
    parts = estimate_cost_parts(
        result.model, result.input_tokens, result.output_tokens
    )
    breakdown = None if parts is None else {
        "input_usd": parts.input_usd,
        "output_usd": parts.output_usd,
        "total_usd": parts.total_usd,
        "output_share": parts.output_share,
    }
    return CallRecord(
        model=result.model,
        attempts=attempts,
        retried=retry_reason is not None,
        retry_reason=retry_reason,
        error=None,
        prompt_version=result.prompt_version,
        schema_valid=True,
        target_skill_fidelity=skill_ok,
        assessment_probe_fidelity=probe_ok,
        scaffold_fidelity=scaffold_ok,
        instruction_mode_fidelity=mode_ok,
        duration_valid=duration_ok,
        material_allowlist_valid=materials_ok,
        deterministic_safety=safety_ok,
        parent_burden={
            "briefing_words": burden.briefing_words,
            "material_count": burden.material_count,
            "step_count": burden.step_count,
            "duration_minutes": burden.duration_minutes,
            "flags": list(burden.flags),
        },
        theme_repetition=not theme_ok,
        hard_failures=hard,
        model_quality_hard_failures=list(hard),
        failure_owner=None if owner is None else owner.value,
        production_would_reject=not safety_ok,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        latency_ms=result.latency_ms,
        estimated_cost_usd=estimate_cost_usd(
            result.model, result.input_tokens, result.output_tokens
        ),
        cost_breakdown=breakdown,
        draft=draft.model_dump(mode="json"),
    )


def _plan_payload(case: BakeoffCase) -> dict[str, Any]:
    plan = case.context.instruction_plan
    return plan.model_dump(mode="json")


def _probe_fidelity(probe: dict[str, object], draft: DailyWinDraft) -> bool:
    task = str(probe.get("observable_task") or "")
    outcome = str(probe.get("expected_outcome") or "")
    target = str(probe.get("target_skill_code") or "")
    if target and draft.primary_skill_code != target:
        return False
    observed = " ".join([draft.observation_focus, *draft.success_checks])
    expected = " ".join(part for part in (task, outcome) if part)
    return _token_overlap(expected, observed)


def _objective_preserved(objective: str, draft: DailyWinDraft) -> bool:
    blob = " ".join([draft.objective, *draft.success_checks, draft.observation_focus])
    return _token_overlap(objective, blob)


def _scaffold_fidelity(scaffold: str, draft: DailyWinDraft) -> bool:
    learn = draft.segments[0]
    blob = _draft_blob(draft).lower()
    if scaffold == "three_step_visual":
        return len(learn.steps) >= 2
    if scaffold == "independent_try":
        return any(hint in blob for hint in ("independent", "on their own", "solo"))
    return len(learn.steps) >= 1


def _mode_fidelity(mode: str, draft: DailyWinDraft) -> bool:
    blob = " ".join(
        [
            draft.objective,
            draft.parent_briefing.purpose,
            draft.parent_briefing.how_to_coach,
            draft.observation_focus,
        ]
    ).lower()
    if mode.lower() in blob:
        return True
    return any(hint in blob for hint in _MODE_HINTS.get(mode, ()))


def _duration_valid(planned: int, draft: DailyWinDraft) -> bool:
    if not (10 <= draft.duration_minutes <= 25):
        return False
    segment_total = sum(segment.minutes for segment in draft.segments)
    if abs(segment_total - draft.duration_minutes) > 2:
        return False
    return abs(draft.duration_minutes - planned) <= 5


def _safety_ok(draft: DailyWinDraft) -> bool:
    try:
        validate_daily_win_safety(draft)
    except SafetyRejectedError:
        return False
    return True


def _theme_not_repeated(draft: DailyWinDraft, recent_themes: list[str]) -> bool:
    if not recent_themes:
        return True
    title = draft.title.strip().lower()
    return all(title != prior.strip().lower() for prior in recent_themes)


def _token_overlap(left: str, right: str) -> bool:
    return bool(_tokens(left) & _tokens(right))


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]{3,}", text.lower())
        if word not in _STOP
    }


def _draft_blob(draft: DailyWinDraft) -> str:
    parts = [
        draft.title,
        draft.objective,
        draft.personalization_summary,
        draft.observation_focus,
        draft.parent_briefing.purpose,
        draft.parent_briefing.how_to_coach,
        *draft.success_checks,
    ]
    for segment in draft.segments:
        parts.append(segment.title)
        parts.append(segment.parent_role)
        parts.extend(segment.steps)
    return " ".join(parts)


def _summarize(rows: list[CallRecord]) -> dict[str, Any]:
    by_model: dict[str, Any] = {}
    for model in BAKEOFF_MODELS:
        items = [row for row in rows if row.model == model]
        costs = [
            row.estimated_cost_usd
            for row in items
            if row.estimated_cost_usd is not None
        ]
        latencies = [row.latency_ms for row in items if row.latency_ms is not None]
        inputs = [row.input_tokens for row in items if row.input_tokens is not None]
        outputs = [row.output_tokens for row in items if row.output_tokens is not None]
        totals = [row.total_tokens for row in items if row.total_tokens is not None]
        hard_counts: dict[str, int] = {}
        quality_counts: dict[str, int] = {}
        for row in items:
            for code in row.hard_failures:
                hard_counts[code] = hard_counts.get(code, 0) + 1
            for code in row.model_quality_hard_failures:
                quality_counts[code] = quality_counts.get(code, 0) + 1
        avg_cost = statistics.mean(costs) if costs else None
        input_cost = [
            (row.cost_breakdown or {}).get("input_usd")
            for row in items
            if row.cost_breakdown
        ]
        output_cost = [
            (row.cost_breakdown or {}).get("output_usd")
            for row in items
            if row.cost_breakdown
        ]
        output_share = [
            (row.cost_breakdown or {}).get("output_share")
            for row in items
            if row.cost_breakdown
        ]
        by_model[model] = {
            "schema_valid": sum(1 for row in items if row.schema_valid),
            "hard_failure_cases": sum(
                1 for row in items if row.model_quality_hard_failures
            ),
            "hard_failures": quality_counts,
            "raw_validator_failures": hard_counts,
            "target_skill_fidelity": _flag_count(items, "target_skill_fidelity"),
            "assessment_probe_fidelity": _flag_count(
                items, "assessment_probe_fidelity"
            ),
            "scaffold_fidelity": _flag_count(items, "scaffold_fidelity"),
            "instruction_mode_fidelity": _flag_count(
                items, "instruction_mode_fidelity"
            ),
            "duration_valid": _flag_count(items, "duration_valid"),
            "material_allowlist_valid": _flag_count(
                items, "material_allowlist_valid"
            ),
            "deterministic_safety": _flag_count(items, "deterministic_safety"),
            "tokens": {
                "input_mean": _mean(inputs),
                "output_mean": _mean(outputs),
                "total_mean": _mean(totals),
                "input_sum": sum(inputs),
                "output_sum": sum(outputs),
                "total_sum": sum(totals),
            },
            "latency_ms": {
                "median": _median(latencies),
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
            },
            "cost_usd": {
                "average_per_win": avg_cost,
                "median_per_win": _median(costs),
                "highest_observed": max(costs) if costs else None,
                "input_mean": _mean(
                    [value for value in input_cost if value is not None]
                ),
                "output_mean": _mean(
                    [value for value in output_cost if value is not None]
                ),
                "output_share_mean": _mean(
                    [value for value in output_share if value is not None]
                ),
                "monthly_estimates": _monthly_estimates(avg_cost),
            },
        }
    return {
        "by_model": by_model,
        "n_cases": 8,
        "cost_ratio_terra_over_luna": _cost_ratio(by_model),
        "note": "n=8; do not overinterpret.",
    }


def _cost_ratio(by_model: dict[str, Any]) -> float | None:
    terra = (by_model.get(TERRA) or {}).get("cost_usd", {}).get("average_per_win")
    luna = (by_model.get(LUNA) or {}).get("cost_usd", {}).get("average_per_win")
    if not terra or not luna:
        return None
    return terra / luna


def _flag_count(items: list[CallRecord], field: str) -> dict[str, int]:
    values = [getattr(item, field) for item in items]
    return {
        "pass": sum(1 for value in values if value is True),
        "fail": sum(1 for value in values if value is False),
        "n_a": sum(1 for value in values if value is None),
    }


def _mean(values: list[int] | list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.mean(values))


def _median(values: list[int] | list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _monthly_estimates(avg_cost: float | None) -> dict[str, Any]:
    if avg_cost is None:
        return {"label": "estimates", "rows": []}
    rows = []
    for children in (100, 1_000, 10_000):
        for wins_per_week in (3, 5):
            monthly = avg_cost * wins_per_week * WEEKS_PER_MONTH * children
            rows.append(
                {
                    "children": children,
                    "wins_per_week": wins_per_week,
                    "estimated_monthly_usd": round(monthly, 2),
                }
            )
    return {
        "label": "estimates",
        "includes": "renderer generation cost only",
        "weeks_per_month": WEEKS_PER_MONTH,
        "rows": rows,
    }


def _recommend(summary: dict[str, Any], *, live: bool) -> dict[str, Any]:
    terra = summary["by_model"][TERRA]
    luna = summary["by_model"][LUNA]
    terra_hard = terra["hard_failure_cases"]
    luna_hard = luna["hard_failure_cases"]
    schema_equal = terra["schema_valid"] == luna["schema_valid"]
    skill_equal = (
        terra["target_skill_fidelity"] == luna["target_skill_fidelity"]
    )
    probe_equal = (
        terra["assessment_probe_fidelity"] == luna["assessment_probe_fidelity"]
    )
    luna_default_ok = (
        live
        and luna_hard == 0
        and terra_hard == 0
        and schema_equal
        and skill_equal
        and probe_equal
    )
    fallback_ok = live and luna_hard <= terra_hard and luna["schema_valid"] >= 7
    if not live:
        verdict = "offline_fake_not_a_decision"
        luna_role = "not_evaluated_live"
    elif luna_hard > terra_hard:
        verdict = "keep_terra_default"
        luna_role = "not_yet_suitable"
    elif luna_hard > 0:
        verdict = "keep_terra_default"
        luna_role = "fallback_candidate"
    elif luna_default_ok:
        verdict = "pending_human_blind_review"
        luna_role = "plausible_default_candidate_pending_human_review"
    elif fallback_ok:
        verdict = "keep_terra_default"
        luna_role = "fallback_candidate"
    else:
        verdict = "keep_terra_default"
        luna_role = "not_yet_suitable"
    return {
        "verdict": verdict,
        "luna_role": luna_role,
        "keep_production_default": TERRA,
        "implement_routing": False,
        "human_scores_pending": True,
        "schema_reliability_equal": schema_equal,
        "planner_fidelity_equal": skill_equal,
        "assessment_fidelity_equal": probe_equal,
        "possible_outcomes": [
            "A: Luna equivalent after human review → Luna renderer, Terra escalation",
            "B: Terra visibly better → retain Terra",
            "C: Mixed by case complexity → investigate routing later",
        ],
        "note": (
            "Automated recommendation only. Do not switch OPENAI_MODEL. "
            "Do not implement routing. Human overall quality is scored in "
            "the blinded review file."
        ),
    }


def _review_markdown(
    cases: tuple[BakeoffCase, ...], rows: list[dict[str, Any]]
) -> str:
    by_id = {row["id"]: row for row in rows}
    lines = [
        "# Daily Win renderer bakeoff — blinded human review",
        "",
        "Not learner data. Do not copy these scores into child tables.",
        "Model identities are hidden. Fill every `A= _` / `B= _` with 1–5.",
        "",
        "Prompt version: `" + PROMPT_VERSION + "`. Schema: DailyWinDraft.",
        "",
        "How to score: replace `_` with a number or choice. Example: "
        "`Educational usefulness: A= 4 B= 5`.",
        "Preference: `A` / `B` / `Tie`. Would use: `A` / `B` / `Both` / `Neither`.",
        "Verdict: `PASS` or `NEEDS REVISION`.",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        row = by_id[case.id]
        assignment = arm_assignment(case.id)
        a_draft = row["outputs"][assignment.a_model]["draft"]
        b_draft = row["outputs"][assignment.b_model]["draft"]
        plan = row["instruction_plan"]
        lines.extend(
            [
                f"## Case {index} — {case.coverage}",
                "",
                "### CASE DESCRIPTION",
                "",
                case.profile_summary,
                "",
                "### Authoritative InstructionPlan",
                "",
                f"- Primary skill: `{plan['primary_skill_code']}`",
                f"- Mode: `{plan['instruction_mode']}`",
                f"- Difficulty: `{plan['intended_difficulty']}`",
                f"- Scaffold: `{plan['scaffold_level']}`",
                f"- Duration: {plan['duration_minutes']} minutes",
                f"- Growth overlay: `{plan.get('growth_target_code') or 'none'}`",
                f"- Assessment objective: {plan['assessment_objective']}",
                "- Probe: "
                + str(
                    (plan.get("assessment_probe") or {}).get("observable_task") or ""
                ),
                "- Theme constraints: "
                + (
                    ", ".join(plan.get("engagement_theme_constraints") or [])
                    or "none"
                ),
                "",
                "### OUTPUT A",
                "",
                _format_win(a_draft),
                "",
                "### OUTPUT B",
                "",
                _format_win(b_draft),
                "",
                *review_score_template(),
            ]
        )
    return "\n".join(lines)


def _format_win(draft: dict[str, Any] | None) -> str:
    if draft is None:
        return "_Generation failed. No parent-facing Daily Win._"
    briefing = draft["parent_briefing"]
    materials = ", ".join(draft["materials"])
    segments = []
    for segment in draft["segments"]:
        steps = "\n".join(f"  - {step}" for step in segment["steps"])
        segments.append(
            "\n".join(
                [
                    f"**{segment['type']} — {segment['title']} "
                    f"({segment['minutes']} min)**",
                    steps,
                    f"  Parent role: {segment['parent_role']}",
                ]
            )
        )
    checks = "\n".join(f"- {item}" for item in draft["success_checks"])
    adaptation = draft.get("adaptation_summary") or "None"
    return "\n".join(
        [
            f"**Title:** {draft['title']}",
            f"**Objective:** {draft['objective']}",
            f"**Duration:** {draft['duration_minutes']} minutes",
            f"**Primary skill:** {draft['primary_skill_code']}",
            "**Supporting skills:** "
            + (", ".join(draft["supporting_skill_codes"]) or "none"),
            f"**Personalization:** {draft['personalization_summary']}",
            f"**Materials:** {materials}",
            "",
            "**Parent briefing**",
            f"- Purpose: {briefing['purpose']}",
            f"- How to coach: {briefing['how_to_coach']}",
            f"- Watch for: {briefing['watch_for']}",
            f"- Avoid: {briefing['avoid']}",
            "",
            *segments,
            "",
            "**If too easy:** " + draft["adaptations"]["if_too_easy"],
            "**If too hard:** " + draft["adaptations"]["if_too_hard"],
            "",
            "**Success checks**",
            checks,
            "",
            f"**Observation focus:** {draft['observation_focus']}",
            f"**Adaptation summary:** {adaptation}",
        ]
    )


def _reveal_payload(
    cases: tuple[BakeoffCase, ...], stamp: str
) -> dict[str, Any]:
    mapping = {}
    for index, case in enumerate(cases, start=1):
        assignment = arm_assignment(case.id)
        mapping[f"case_{index}"] = {
            "bakeoff_id": case.id,
            "coverage": case.coverage,
            "A": assignment.a_model,
            "B": assignment.b_model,
        }
    return {
        "created_at_stamp": stamp,
        "algorithm": f"sha256({BLIND_SALT}|case_id)[0] % 2 == 0 => A=terra",
        "note": (
            "Reveal mapping only. Not learner data. Keep hidden until "
            "human scores are complete."
        ),
        "assignment": mapping,
    }


def assert_review_is_blind(markdown: str) -> None:
    lowered = markdown.lower()
    for needle in ("gpt-5.6-terra", "gpt-5.6-luna"):
        if needle in lowered:
            raise ValueError(f"review leaked model identity: {needle}")


def dump_case_context_json(case: BakeoffCase) -> str:
    return case.context.model_dump_json()
