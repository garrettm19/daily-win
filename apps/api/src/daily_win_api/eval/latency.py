"""Generation-latency eval. Offline by default. Live Terra only with --live."""

from __future__ import annotations

import inspect
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from daily_win_api.ai.exceptions import ModelGatewayError, ModelGatewaySchemaError
from daily_win_api.ai.gateway import build_model_gateway
from daily_win_api.ai.prompts.current import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from daily_win_api.ai.providers.fake import FakeModelGateway
from daily_win_api.ai.providers.openai import OpenAIModelGateway
from daily_win_api.ai.schemas import DailyWinModelContext
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, get_settings
from daily_win_api.domains.daily_wins.latency import GenerationTimer, bind_timer, span
from daily_win_api.domains.daily_wins.renderer_contract import (
    plan_with_contracts,
    renderer_contract_hard_failures,
)
from daily_win_api.eval.fixtures import load_eval_fixtures
from daily_win_api.eval.scoring import write_results

READY_HOME_P50_MS = 500
READY_HOME_P95_MS = 1000
REFLECTION_TARGET_MS = 1000
REPRESENTATIVE_MODES = (
    "introduce",
    "diagnostic",
    "practice",
    "remediation",
    "review",
)
MAX_LIVE_BASELINE = 5


@dataclass(frozen=True)
class LatencyCaseResult:
    mode: str
    total_ms: int
    provider_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    attempts: int
    schema_pass: bool
    renderer_contract_pass: bool
    contract_failures: tuple[str, ...]
    error_code: str | None
    model: str
    prompt_version: str


def run_latency_suite() -> list[str]:
    """Offline instrumentation and configuration checks. No live model."""
    errors: list[str] = []
    timer = GenerationTimer()
    with bind_timer(timer):
        with span("scheduler"):
            time.sleep(0)
        with timer.span("provider_ms"):
            time.sleep(0)
    payload = timer.as_dict()
    for key in ("total_ms", "scheduler", "provider_ms"):
        if key not in payload:
            errors.append(f"timer missing {key}")
    if payload["total_ms"] < 0:
        errors.append("timer total_ms negative")

    params = inspect.signature(OpenAIModelGateway.__init__).parameters
    if "reasoning_effort" not in params:
        errors.append("OpenAI gateway missing optional reasoning_effort")
    if "service_tier" not in params:
        errors.append("OpenAI gateway missing optional service_tier")
    production = inspect.signature(build_model_gateway)
    if "reasoning_effort" in production.parameters:
        errors.append("build_model_gateway must not take production reasoning routing")

    if not SYSTEM_PROMPT.startswith("You are Daily Win"):
        errors.append("system prompt prefix unexpected")
    user = build_user_prompt('{"nickname":"Hayes"}')
    if not user.startswith("Create one Daily Win"):
        errors.append("user prompt prefix unexpected")
    if PROMPT_VERSION != "daily_win_generator_v5":
        errors.append(f"unexpected prompt {PROMPT_VERSION}")

    fixture = freeze_mode_context("practice")
    fake = FakeModelGateway()
    result = fake.generate_daily_win(fixture)
    if result.latency_ms is None:
        errors.append("fake gateway omitted latency_ms")
    return errors


def freeze_mode_context(mode: str) -> DailyWinModelContext:
    base = load_eval_fixtures()[0].context
    plan = plan_with_contracts(
        base.instruction_plan.model_copy(update={"instruction_mode": mode})
    )
    return base.model_copy(update={"instruction_plan": plan})


def run_latency_baseline(*, live: bool) -> dict[str, Any]:
    """At most five Terra generations when live. Fake otherwise."""
    settings = get_settings()
    if live and not settings.openai_configured:
        raise SystemExit("Live latency baseline requires OPENAI_API_KEY.")
    gateway = (
        build_model_gateway(
            settings.model_copy(update={"openai_model": DEFAULT_OPENAI_MODEL})
        )
        if live
        else FakeModelGateway()
    )
    rows: list[LatencyCaseResult] = []
    for mode in REPRESENTATIVE_MODES[:MAX_LIVE_BASELINE]:
        rows.append(_run_one(gateway, mode, live=live))
    provider_share = _provider_share(rows)
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "live": live,
        "model": DEFAULT_OPENAI_MODEL if live else "fake-model",
        "prompt_version": PROMPT_VERSION,
        "case_count": len(rows),
        "live_calls": len(rows) if live else 0,
        "provider_latency_share": provider_share,
        "budgets": {
            "ready_home_p50_ms": READY_HOME_P50_MS,
            "ready_home_p95_ms": READY_HOME_P95_MS,
            "reflection_target_ms": REFLECTION_TARGET_MS,
        },
        "openai_reasoning_kwarg_supported": "reasoning_effort"
        in inspect.signature(OpenAIModelGateway.__init__).parameters,
        "openai_service_tier_kwarg_supported": "service_tier"
        in inspect.signature(OpenAIModelGateway.__init__).parameters,
        "production_reasoning_effort": None,
        "production_service_tier": None,
        "prompt_cache_note": (
            "System prompt is a stable first message; user JSON follows. "
            "No semantic reorder applied."
        ),
        "results": [asdict(row) for row in rows],
        "note": (
            "Synthetic InstructionPlans only. Terra remains default. "
            "Not learner memory."
        ),
    }


def write_latency_baseline(path, *, live: bool) -> None:
    write_results(path, run_latency_baseline(live=live))


def _run_one(gateway, mode: str, *, live: bool) -> LatencyCaseResult:
    context = freeze_mode_context(mode)
    started = time.perf_counter()
    error_code = None
    result = None
    try:
        result = gateway.generate_daily_win(context)
        schema_pass = True
        hard = renderer_contract_hard_failures(result.draft, context.instruction_plan)
    except (ModelGatewaySchemaError, ModelGatewayError) as exc:
        schema_pass = False
        hard = ()
        error_code = exc.code
    total_ms = int((time.perf_counter() - started) * 1000)
    return LatencyCaseResult(
        mode=mode,
        total_ms=total_ms,
        provider_ms=None if result is None else result.latency_ms,
        input_tokens=None if result is None else result.input_tokens,
        output_tokens=None if result is None else result.output_tokens,
        cached_input_tokens=None if result is None else result.cached_input_tokens,
        attempts=1,
        schema_pass=schema_pass,
        renderer_contract_pass=schema_pass and not hard,
        contract_failures=tuple(hard),
        error_code=error_code,
        model=(
            DEFAULT_OPENAI_MODEL
            if live
            else (result.model if result is not None else "fake-model")
        ),
        prompt_version=PROMPT_VERSION,
    )


def _provider_share(rows: list[LatencyCaseResult]) -> float | None:
    usable = [
        (row.provider_ms, row.total_ms)
        for row in rows
        if row.provider_ms is not None and row.total_ms > 0
    ]
    if not usable:
        return None
    provider = sum(item[0] for item in usable)
    total = sum(item[1] for item in usable)
    return round(provider / total, 4) if total else None
