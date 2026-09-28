"""Terra reasoning-effort and service-tier calibration. Max 12 live calls."""

from __future__ import annotations

import inspect
import json
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from daily_win_api.ai.delivery import (
    BACKGROUND_PREP,
    INTERACTIVE_WAIT,
    bind_delivery,
)
from daily_win_api.ai.exceptions import ModelGatewayError, ModelGatewaySchemaError
from daily_win_api.ai.gateway import build_model_gateway
from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.ai.providers.openai import OpenAIModelGateway
from daily_win_api.ai.schemas import DailyWinDraft, DailyWinGenerationResult
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, get_settings
from daily_win_api.domains.daily_wins.first_win import (
    ready_before_guide,
    visible_wait_ms,
)
from daily_win_api.domains.daily_wins.renderer_contract import (
    contracts_for_plan,
    renderer_contract_hard_failures,
)
from daily_win_api.domains.daily_wins.safety import validate_daily_win_safety
from daily_win_api.domains.daily_wins.schemas import SafetyRejectedError
from daily_win_api.domains.learning.coach_protocol import build_coach_protocol
from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel
from daily_win_api.eval.latency import freeze_mode_context
from daily_win_api.eval.output_audit import audit_payload
from daily_win_api.eval.pricing import estimate_cost_usd
from daily_win_api.eval.renderer_quality import parent_burden
from daily_win_api.eval.scoring import write_results

FROZEN_MODES = ("diagnostic", "remediation", "introduce")
REASONING_EFFORTS = ("none", "low", "medium")
MAX_REASONING_CALLS = 9
MAX_TIER_CALLS = 3
MAX_LIVE_CALLS = MAX_REASONING_CALLS + MAX_TIER_CALLS
MAX_PRIORITY_CALLS = 3
EXISTING_LIVE_STEM = "20260921T201524Z-terra-config-live"
SERVICE_TIER_CANDIDATES = ("fast", "priority")
REVIEW_DIMENSIONS = (
    ("educational_usefulness", "Educational usefulness"),
    ("plan_fidelity", "Plan fidelity"),
    ("age_appropriateness", "Age appropriateness"),
    ("parent_clarity", "Parent clarity"),
    ("engagement", "Engagement"),
    ("assessment_quality", "Assessment quality"),
    ("coaching_quality", "Coaching quality"),
    ("overall", "Overall"),
)


@dataclass(frozen=True)
class TerraConfigRow:
    mode: str
    reasoning_effort: str
    service_tier: str | None
    requested_service_tier: str | None
    returned_service_tier: str | None
    total_ms: int
    provider_ms: int | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    schema_pass: bool
    renderer_contract_pass: bool
    safety_pass: bool
    parent_burden_flags: tuple[str, ...]
    error_code: str | None
    estimated_usd: float | None
    letter: str | None = None


def run_terra_config_offline_checks() -> list[str]:
    errors: list[str] = []
    params = inspect.signature(OpenAIModelGateway.__init__).parameters
    if "reasoning_effort" not in params or "service_tier" not in params:
        errors.append("OpenAI gateway missing optional Terra config kwargs")
    production = inspect.signature(build_model_gateway)
    if "reasoning_effort" in production.parameters:
        errors.append("production gateway must not route reasoning effort")
    if "service_tier" in production.parameters:
        errors.append("production gateway must not route service tier")
    if "intent" in production.parameters:
        errors.append("production gateway must not take generation intent")
    if visible_wait_ms(28300, 22100) != 6200:
        errors.append("visible wait example mismatch")
    if visible_wait_ms(1000, 4000) != 0:
        errors.append("visible wait must clamp at zero")
    if ready_before_guide(10000, 20000) is not True:
        errors.append("ready_before_guide should be true when Guide outlasts Terra")
    if ready_before_guide(30000, 20000) is not False:
        errors.append("ready_before_guide should be false when Terra outlasts Guide")
    if ready_before_guide(10000, None) is not None:
        errors.append("ready_before_guide unknown without onboarding dwell")
    audit = audit_payload()
    if not audit["fields"]:
        errors.append("output audit empty")
    fake = FakeModelGateway(reasoning_effort="low", service_tier="fast")
    result = fake.generate_daily_win(freeze_mode_context("diagnostic"))
    if result.reasoning_effort != "low" or result.service_tier != "fast":
        errors.append("fake gateway did not echo Terra config")
    background = bind_delivery(FakeModelGateway(), BACKGROUND_PREP)
    bg = background.generate_daily_win(freeze_mode_context("diagnostic"))
    if bg.reasoning_effort != "medium" or bg.requested_service_tier != "default":
        errors.append("background delivery must be medium/default")
    if bg.service_tier != "default":
        errors.append("background returned tier should be default")
    interactive = bind_delivery(FakeModelGateway(), INTERACTIVE_WAIT)
    ix = interactive.generate_daily_win(freeze_mode_context("introduce"))
    if ix.reasoning_effort != "medium" or ix.requested_service_tier != "fast":
        errors.append("interactive delivery must be medium/fast")
    if ix.service_tier != "priority":
        errors.append("interactive fake should echo returned priority")
    return errors


def run_terra_config(*, live: bool) -> dict[str, Any]:
    settings = get_settings()
    if live and not settings.openai_configured:
        raise SystemExit("Live Terra config requires OPENAI_API_KEY.")
    rng = random.Random(42)
    reasoning_rows: list[TerraConfigRow] = []
    drafts: dict[tuple[str, str], DailyWinDraft] = {}
    live_calls = 0
    for mode in FROZEN_MODES:
        letters = list("ABC")
        rng.shuffle(letters)
        for effort, letter in zip(REASONING_EFFORTS, letters, strict=True):
            if live and live_calls >= MAX_REASONING_CALLS:
                break
            row, draft = _run_one(
                mode=mode,
                reasoning_effort=effort,
                service_tier=None,
                live=live,
                settings=settings,
                letter=letter,
            )
            reasoning_rows.append(row)
            if draft is not None:
                drafts[(mode, effort)] = draft
            if live:
                live_calls += 1

    assignment = {
        f"case_{index}": {
            "mode": mode,
            "A": next(
                row.reasoning_effort
                for row in reasoning_rows
                if row.mode == mode and row.letter == "A"
            ),
            "B": next(
                row.reasoning_effort
                for row in reasoning_rows
                if row.mode == mode and row.letter == "B"
            ),
            "C": next(
                row.reasoning_effort
                for row in reasoning_rows
                if row.mode == mode and row.letter == "C"
            ),
        }
        for index, mode in enumerate(FROZEN_MODES, start=1)
        if any(row.mode == mode for row in reasoning_rows)
    }

    best_effort = _best_acceptable_effort(reasoning_rows)
    tier_probe = _probe_service_tier(
        live=live,
        settings=settings,
        effort=best_effort,
        live_calls=live_calls,
    )
    live_calls = tier_probe["live_calls"]
    tier_rows: list[TerraConfigRow] = list(tier_probe["rows"])

    by_effort = _summarize_effort(reasoning_rows)
    decision_matrix = [
        {
            "configuration": f"Terra {effort}/default",
            "median_provider_ms": by_effort[effort]["median_provider_ms"],
            "schema_pass": by_effort[effort]["schema_pass"],
            "renderer_contract_pass": by_effort[effort]["renderer_contract_pass"],
            "safety_pass": by_effort[effort]["safety_pass"],
            "parent_burden_flags": by_effort[effort]["parent_burden_flags"],
            "estimated_usd_sum": by_effort[effort]["estimated_usd_sum"],
            "n": by_effort[effort]["n"],
            "candidate_use": _candidate_use(effort, best_effort, live=live),
        }
        for effort in REASONING_EFFORTS
    ]
    if tier_rows:
        decision_matrix.append(
            {
                "configuration": (
                    f"Terra {best_effort}/"
                    f"{tier_rows[0].requested_service_tier or 'probe'}"
                ),
                "median_provider_ms": _median(
                    [row.provider_ms for row in tier_rows if row.provider_ms]
                ),
                "returned_service_tier": [
                    row.returned_service_tier for row in tier_rows
                ],
                "n": len(tier_rows),
                "candidate_use": (
                    "Synchronous fallback candidate only. "
                    "Do not enable globally."
                ),
            }
        )

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "live": live,
        "model": DEFAULT_OPENAI_MODEL if live else "fake-model",
        "prompt_version": PROMPT_VERSION,
        "production_reasoning_effort": None,
        "production_service_tier": None,
        "live_calls": live_calls if live else 0,
        "max_live_calls": MAX_LIVE_CALLS,
        "n_note": "n=3 frozen plans per effort. Do not overstate.",
        "luna_not_revisited": True,
        "config_changed": False,
        "reasoning": [asdict(row) for row in reasoning_rows],
        "service_tier": {
            "supported": tier_probe["supported"],
            "error_code": tier_probe["error_code"],
            "rows": [asdict(row) for row in tier_rows],
        },
        "assignment": assignment,
        "best_acceptable_effort": best_effort,
        "decision_matrix": decision_matrix,
        "output_audit": audit_payload(next(iter(drafts.values()), None)),
        "background_vs_sync_policy": {
            "attractive": True,
            "implemented": False,
            "note": (
                "Paying for fast/priority only while a parent waits is "
                "architecturally attractive if request-level tier is supported "
                "and a lower effort remains quality-safe. Not enabled."
            ),
        },
        "note": (
            "Synthetic InstructionPlans only. Terra remains default. "
            "Not learner memory. Production reasoning/tier unchanged."
        ),
    }


def write_terra_config(directory: Path, *, live: bool) -> dict[str, Path]:
    payload = run_terra_config(live=live)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    mode = "live" if live else "fake"
    json_path = directory / f"{stamp}-terra-config-{mode}.json"
    review_path = directory / f"{stamp}-terra-config-{mode}-review.md"
    reveal_path = directory / f"{stamp}-terra-config-{mode}-reveal.json"
    write_results(json_path, payload)
    review_path.write_text(_review_markdown(payload), encoding="utf-8")
    write_results(
        reveal_path,
        {
            "created_at": payload["created_at"],
            "live": live,
            "assignment": payload["assignment"],
            "note": "Keep sealed until human scores are filled.",
        },
    )
    return {"json": json_path, "review": review_path, "reveal": reveal_path}


def _run_one(
    *,
    mode: str,
    reasoning_effort: str,
    service_tier: str | None,
    live: bool,
    settings,
    letter: str | None,
) -> tuple[TerraConfigRow, DailyWinDraft | None]:
    import time

    context = freeze_mode_context(mode)
    gateway: Any
    if live:
        gateway = OpenAIModelGateway(
            api_key=settings.openai_api_key or "",
            model=DEFAULT_OPENAI_MODEL,
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
        )
    else:
        gateway = FakeModelGateway(
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
        )
    started = time.perf_counter()
    error_code = None
    result: DailyWinGenerationResult | None = None
    schema_pass = False
    renderer_pass = False
    safety_pass = False
    burden: tuple[str, ...] = ()
    draft = None
    try:
        result = gateway.generate_daily_win(context)
        schema_pass = True
        draft = result.draft
        hard = renderer_contract_hard_failures(draft, context.instruction_plan)
        renderer_pass = not hard
        try:
            validate_daily_win_safety(draft)
            safety_pass = True
        except SafetyRejectedError:
            safety_pass = False
        burden = tuple(parent_burden(draft).flags)
    except (ModelGatewaySchemaError, ModelGatewayError) as exc:
        error_code = exc.code
    total_ms = int((time.perf_counter() - started) * 1000)
    estimated = None
    if result is not None:
        estimated = estimate_cost_usd(
            DEFAULT_OPENAI_MODEL if live else result.model,
            result.input_tokens,
            result.output_tokens,
            service_tier=result.service_tier or service_tier,
        )
    row = TerraConfigRow(
        mode=mode,
        reasoning_effort=reasoning_effort,
        service_tier=None if result is None else result.service_tier,
        requested_service_tier=service_tier,
        returned_service_tier=None if result is None else result.service_tier,
        total_ms=total_ms,
        provider_ms=None if result is None else result.latency_ms,
        input_tokens=None if result is None else result.input_tokens,
        cached_input_tokens=None if result is None else result.cached_input_tokens,
        output_tokens=None if result is None else result.output_tokens,
        reasoning_tokens=None if result is None else result.reasoning_tokens,
        schema_pass=schema_pass,
        renderer_contract_pass=renderer_pass,
        safety_pass=safety_pass,
        parent_burden_flags=burden,
        error_code=error_code,
        estimated_usd=estimated,
        letter=letter,
    )
    return row, draft


def _probe_service_tier(
    *, live: bool, settings, effort: str, live_calls: int
) -> dict[str, Any]:
    if not live:
        return {"supported": None, "error_code": None, "rows": [], "live_calls": 0}
    remaining = MAX_LIVE_CALLS - live_calls
    if remaining <= 0:
        return {
            "supported": None,
            "error_code": "live_budget_exhausted",
            "rows": [],
            "live_calls": live_calls,
        }
    chosen_tier = None
    probe_error = None
    for candidate in SERVICE_TIER_CANDIDATES:
        if live_calls >= MAX_LIVE_CALLS:
            break
        row, _draft = _run_one(
            mode=FROZEN_MODES[0],
            reasoning_effort=effort,
            service_tier=candidate,
            live=True,
            settings=settings,
            letter=None,
        )
        live_calls += 1
        if row.error_code in {"provider_bad_request", "provider_error"}:
            probe_error = row.error_code
            continue
        chosen_tier = candidate
        rows = [row]
        for mode in FROZEN_MODES[1:]:
            if live_calls >= MAX_LIVE_CALLS or len(rows) >= MAX_TIER_CALLS:
                break
            extra, _ = _run_one(
                mode=mode,
                reasoning_effort=effort,
                service_tier=chosen_tier,
                live=True,
                settings=settings,
                letter=None,
            )
            live_calls += 1
            rows.append(extra)
        return {
            "supported": True,
            "error_code": None,
            "rows": rows,
            "live_calls": live_calls,
        }
    return {
        "supported": False,
        "error_code": probe_error,
        "rows": [],
        "live_calls": live_calls,
    }


def _best_acceptable_effort(rows: list[TerraConfigRow]) -> str:
    grouped: dict[str, list[TerraConfigRow]] = {
        effort: [] for effort in REASONING_EFFORTS
    }
    for row in rows:
        grouped[row.reasoning_effort].append(row)
    medium = grouped["medium"]
    medium_ok = bool(medium) and all(
        item.schema_pass and item.renderer_contract_pass and item.safety_pass
        for item in medium
    )
    for effort in ("low", "none"):
        cohort = grouped[effort]
        if not cohort:
            continue
        ok = all(
            item.schema_pass and item.renderer_contract_pass and item.safety_pass
            for item in cohort
        )
        if ok and medium_ok:
            return effort
        if ok and not medium_ok:
            return effort
    return "medium"


def _candidate_use(effort: str, best: str, *, live: bool) -> str:
    if not live:
        return "Offline fake only. Not a production recommendation."
    if effort == "none" and best != "none":
        return "Reject if quality is materially worse than medium."
    if effort == best and effort != "medium":
        return "Candidate after human review. Production unchanged."
    if effort == "medium":
        return (
            "Current production default (unspecified). "
            "Keep unless review says otherwise."
        )
    return "Not selected from structural checks."


def _summarize_effort(rows: list[TerraConfigRow]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for effort in REASONING_EFFORTS:
        cohort = [row for row in rows if row.reasoning_effort == effort]
        providers = [row.provider_ms for row in cohort if row.provider_ms is not None]
        costs = [row.estimated_usd for row in cohort if row.estimated_usd is not None]
        flags: list[str] = []
        for row in cohort:
            flags.extend(row.parent_burden_flags)
        summary[effort] = {
            "n": len(cohort),
            "median_provider_ms": _median(providers),
            "schema_pass": all(row.schema_pass for row in cohort) if cohort else False,
            "renderer_contract_pass": all(row.renderer_contract_pass for row in cohort)
            if cohort
            else False,
            "safety_pass": all(row.safety_pass for row in cohort) if cohort else False,
            "parent_burden_flags": sorted(set(flags)),
            "estimated_usd_sum": round(sum(costs), 6) if costs else None,
        }
    return summary


def _median(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return int((ordered[mid - 1] + ordered[mid]) / 2)


def _review_markdown(payload: dict[str, Any]) -> str:
    return _complete_blind_review_markdown(payload, drafts={})


def expand_blind_review_from_artifact(json_path: Path) -> Path:
    """Rebuild the A/B/C review from stored metrics. No live calls."""
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    review_path = json_path.with_name(json_path.stem + "-review.md")
    review_path.write_text(
        _complete_blind_review_markdown(payload, drafts={}),
        encoding="utf-8",
    )
    return review_path


def write_medium_priority_probe(directory: Path, *, live: bool) -> dict[str, Path]:
    payload = run_medium_priority_probe(live=live, directory=directory)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    mode = "live" if live else "fake"
    json_path = directory / f"{stamp}-terra-medium-priority-{mode}.json"
    write_results(json_path, payload)
    return {"json": json_path}


def run_medium_priority_probe(
    *, live: bool, directory: Path | None = None
) -> dict[str, Any]:
    settings = get_settings()
    if live and not settings.openai_configured:
        raise SystemExit("Live Terra priority probe requires OPENAI_API_KEY.")
    rows: list[dict[str, Any]] = []
    live_calls = 0
    for mode in FROZEN_MODES:
        if live and live_calls >= MAX_PRIORITY_CALLS:
            break
        row, draft = _run_one(
            mode=mode,
            reasoning_effort="medium",
            service_tier="fast",
            live=live,
            settings=settings,
            letter=None,
        )
        if live:
            live_calls += 1
        item = asdict(row)
        item["draft"] = None if draft is None else draft.model_dump(mode="json")
        rows.append(item)
    existing = None
    if directory is not None:
        prior = directory / f"{EXISTING_LIVE_STEM}.json"
        if prior.exists():
            existing = json.loads(prior.read_text(encoding="utf-8"))
    comparison = _compare_priority_cohorts(existing, rows)
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "live": live,
        "model": DEFAULT_OPENAI_MODEL if live else "fake-model",
        "prompt_version": PROMPT_VERSION,
        "reasoning_effort": "medium",
        "requested_service_tier": "fast",
        "live_calls": live_calls if live else 0,
        "max_live_calls": MAX_PRIORITY_CALLS,
        "n_note": "n=3 frozen plans. Do not overstate.",
        "luna_not_revisited": True,
        "production_reasoning_effort_unchanged": True,
        "rows": rows,
        "comparison": comparison,
        "note": (
            "Synthetic InstructionPlans only. Same prompt v5 / contracts / "
            "validator as production. Not learner memory."
        ),
    }


def _compare_priority_cohorts(
    existing: dict[str, Any] | None, priority_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    medium_default = _rows_matching(
        existing, reasoning_effort="medium", requested_service_tier=None
    )
    low_priority = _rows_matching(
        existing, reasoning_effort="low", requested_service_tier="fast"
    )
    return {
        "medium_default": _cohort_summary(medium_default, label="medium/default"),
        "low_priority": _cohort_summary(low_priority, label="low/priority"),
        "medium_priority": _cohort_summary(priority_rows, label="medium/priority"),
        "cost_policy": _priority_cost_policy(medium_default, priority_rows),
        "n_note": "Each cell is n=3. Do not overstate.",
    }


def _rows_matching(
    existing: dict[str, Any] | None,
    *,
    reasoning_effort: str,
    requested_service_tier: str | None,
) -> list[dict[str, Any]]:
    if not existing:
        return []
    if requested_service_tier is None:
        return [
            row
            for row in existing.get("reasoning") or []
            if row.get("reasoning_effort") == reasoning_effort
        ]
    return [
        row
        for row in (existing.get("service_tier") or {}).get("rows") or []
        if row.get("reasoning_effort") == reasoning_effort
        and row.get("requested_service_tier") == requested_service_tier
    ]


def _cohort_summary(rows: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    providers = [
        int(row["provider_ms"])
        for row in rows
        if row.get("provider_ms") is not None
    ]
    totals = [int(row["total_ms"]) for row in rows if row.get("total_ms") is not None]
    return {
        "label": label,
        "n": len(rows),
        "median_provider_ms": _median(providers),
        "median_total_ms": _median(totals),
        "input_tokens": [row.get("input_tokens") for row in rows],
        "cached_input_tokens": [row.get("cached_input_tokens") for row in rows],
        "output_tokens": [row.get("output_tokens") for row in rows],
        "reasoning_tokens": [row.get("reasoning_tokens") for row in rows],
        "schema_pass": all(row.get("schema_pass") for row in rows) if rows else False,
        "renderer_contract_pass": (
            all(row.get("renderer_contract_pass") for row in rows) if rows else False
        ),
        "safety_pass": all(row.get("safety_pass") for row in rows) if rows else False,
        "requested_service_tier": [row.get("requested_service_tier") for row in rows],
        "returned_service_tier": [row.get("returned_service_tier") for row in rows],
        "estimated_usd": [row.get("estimated_usd") for row in rows],
        "estimated_usd_sum": _sum_costs(rows),
    }


def _priority_cost_policy(
    medium_default: list[dict[str, Any]],
    priority_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    standard = _mean_cost(medium_default)
    fast = _mean_cost(priority_rows)
    incremental = None
    if standard is not None and fast is not None:
        incremental = round(fast - standard, 6)
    rates = (0.01, 0.05, 0.10)
    mixed = None
    if incremental is not None:
        mixed = {
            f"{int(rate * 100)}pct_interactive": round(incremental * rate, 6)
            for rate in rates
        }
    return {
        "standard_usd_per_win": standard,
        "priority_usd_per_win": fast,
        "incremental_usd_per_interactive_win": incremental,
        "fast_mode_multiplier": 2.0,
        "mixed_incremental_usd_per_win": mixed,
        "note": (
            "Priority only on INTERACTIVE_WAIT. Background stays Standard. "
            "Do not assume every Win uses Fast mode."
        ),
    }


def _mean_cost(rows: list[dict[str, Any]]) -> float | None:
    values = [
        float(row["estimated_usd"])
        for row in rows
        if row.get("estimated_usd") is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _sum_costs(rows: list[dict[str, Any]]) -> float | None:
    values = [
        float(row["estimated_usd"])
        for row in rows
        if row.get("estimated_usd") is not None
    ]
    if not values:
        return None
    return round(sum(values), 6)


def _complete_blind_review_markdown(
    payload: dict[str, Any],
    *,
    drafts: dict[tuple[str, str], DailyWinDraft],
) -> str:
    lines = [
        "# Terra reasoning-effort blind review (V0.4.2 / V0.4.2a)",
        "",
        "Do not reveal which letter is none, low, or medium.",
        "Score 1–5. Verdict: PASS or NEEDS REVISION.",
        "Preference: A / B / C / Tie.",
        "",
        "Draft bodies were not stored in the original live JSON "
        "(`store=False`; metrics rows had no draft field). Do not invent "
        "Daily Win text. Frozen InstructionPlan, CoachProtocol, and renderer "
        "contracts are identical for A/B/C of each case and are included so "
        "the review can still judge plan fidelity against the required "
        "structure. `none` cannot be accepted from this artifact alone.",
        "",
    ]
    assignment = payload.get("assignment") or {}
    reasoning = payload.get("reasoning") or []
    for index, mode in enumerate(FROZEN_MODES, start=1):
        key = f"case_{index}"
        if key not in assignment:
            continue
        lines.append(f"## Case {index} — {mode}")
        lines.append("")
        lines.extend(_frozen_plan_markdown(mode))
        lines.append("")
        for letter in "ABC":
            row = next(
                (
                    item
                    for item in reasoning
                    if item["mode"] == mode and item.get("letter") == letter
                ),
                None,
            )
            lines.append(f"### Output {letter}")
            lines.append("")
            draft = drafts.get((mode, letter))
            lines.extend(_output_body_markdown(row, draft))
            lines.append("")
        lines.append("### Scores")
        lines.append("")
        for _key, label in REVIEW_DIMENSIONS:
            lines.append(f"{label}: A= _ B= _ C= _")
        lines.extend(
            [
                "Preference: A / B / C / Tie",
                "Verdict A: PASS / NEEDS REVISION",
                "Verdict B: PASS / NEEDS REVISION",
                "Verdict C: PASS / NEEDS REVISION",
                "Overall verdict: PASS / NEEDS REVISION",
                "Note:",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _output_body_markdown(
    row: dict[str, Any] | None, draft: DailyWinDraft | None
) -> list[str]:
    if draft is not None:
        return _draft_markdown(draft)
    lines = [
        "**Daily Win (parent-facing)**",
        "",
        "_Not persisted in the source metrics JSON. Do not reconstruct from "
        "latency or token counts — those would unblind reasoning identity._",
        "",
    ]
    if row is None:
        lines.append("_Missing metrics row._")
        return lines
    lines.extend(
        [
            f"Schema: {'pass' if row['schema_pass'] else 'fail'}",
            f"Renderer contract: "
            f"{'pass' if row['renderer_contract_pass'] else 'fail'}",
            f"Safety: {'pass' if row['safety_pass'] else 'fail'}",
            "Parent-burden flags: "
            f"{row['parent_burden_flags'] or 'none'}",
        ]
    )
    return lines


def _draft_markdown(draft: DailyWinDraft) -> list[str]:
    briefing = draft.parent_briefing
    lines = [
        "**Daily Win (parent-facing)**",
        "",
        f"**Title:** {draft.title}",
        f"**Objective:** {draft.objective}",
        f"**Duration:** {draft.duration_minutes} minutes",
        f"**Skill:** {draft.primary_skill_code}",
        f"**Personalization:** {draft.personalization_summary}",
        f"**Materials:** {', '.join(item.value for item in draft.materials)}",
        "",
        "Parent briefing:",
        f"- Purpose: {briefing.purpose}",
        f"- How to coach: {briefing.how_to_coach}",
        f"- Watch for: {briefing.watch_for}",
        f"- Avoid: {briefing.avoid}",
        "",
    ]
    for segment in draft.segments:
        lines.append(f"{segment.type.value} — {segment.title} ({segment.minutes} min)")
        lines.append(f"Parent role: {segment.parent_role}")
        for step in segment.steps:
            lines.append(f"- {step}")
        lines.append("")
    lines.extend(
        [
            f"If too easy: {draft.adaptations.if_too_easy}",
            f"If too hard: {draft.adaptations.if_too_hard}",
            "Success checks:",
        ]
    )
    for check in draft.success_checks:
        lines.append(f"- {check}")
    lines.extend(
        [
            f"Observation focus: {draft.observation_focus}",
            "",
        ]
    )
    return lines


def _frozen_plan_markdown(mode: str) -> list[str]:
    context = freeze_mode_context(mode)
    plan = context.instruction_plan
    contracts = contracts_for_plan(plan)
    protocol = build_coach_protocol(
        instruction_mode=InstructionMode(plan.instruction_mode),
        scaffold=ScaffoldLevel(plan.scaffold_level),
        age_years=context.parent_reported_baseline.age_years,
        skill_code=plan.primary_skill_code,
        academic_band=plan.academic_band,
        growth_target_code=plan.growth_target_code,
    )
    lines = [
        "### Frozen InstructionPlan (shared by A/B/C)",
        "",
        f"- Mode: {plan.instruction_mode}",
        f"- Primary skill: {plan.primary_skill_code}",
        f"- Supporting skill: {plan.supporting_skill_code or 'none'}",
        f"- Difficulty: {plan.intended_difficulty}",
        f"- Scaffold: {plan.scaffold_level}",
        f"- Duration: {plan.duration_minutes} minutes",
        f"- Assessment objective: {plan.assessment_objective}",
        f"- Assessment probe: {plan.assessment_probe}",
        f"- Desired evidence: {plan.desired_evidence}",
        f"- Prerequisite rationale: {plan.prerequisite_rationale}",
        f"- Growth target: {plan.growth_target_code or 'none'}",
        f"- Growth adaptation: {plan.growth_adaptation_summary or 'none'}",
        f"- Presentation constraint: {plan.presentation_constraint or 'none'}",
        f"- Policy: {plan.policy_version}",
        "",
        "### Required CoachProtocol (shared by A/B/C)",
        "",
        f"- Coach goal: {protocol.coach_goal}",
        f"- Expected challenge: {protocol.expected_challenge_level}",
        f"- Prompt ceiling: {protocol.prompt_ceiling}",
        f"- Initial wait: {protocol.initial_wait_behavior}",
        f"- Assessment boundary: {protocol.assessment_boundary}",
        f"- Why this coaching: {protocol.why_this_coaching}",
        f"- Independence goal: {protocol.independence_goal}",
        f"- Correction: {protocol.correction_policy}",
        f"- Struggle: {protocol.struggle_policy}",
        f"- Success: {protocol.success_response}",
        f"- Frustration: {protocol.frustration_response}",
        "- Coach card:",
    ]
    for item in protocol.coach_card:
        lines.append(f"  - {item}")
    lines.append("- Cues:")
    for cue in protocol.cues:
        lines.append(f"  - {cue.label}: {cue.text}")
    lines.extend(
        [
            "",
            "### Renderer contracts (shared by A/B/C)",
            "",
        ]
    )
    for rule in contracts:
        lines.append(f"- {rule}")
    planned = tuple(plan.renderer_contracts or ())
    if planned and planned != contracts:
        lines.append(f"- Plan-listed contracts: {list(planned)}")
    return lines
