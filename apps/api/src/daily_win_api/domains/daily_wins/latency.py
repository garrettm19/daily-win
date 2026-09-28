"""Generation timing. No child narrative. Not production telemetry architecture."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

logger = logging.getLogger(__name__)

_TIMER: ContextVar[GenerationTimer | None] = ContextVar(
    "daily_win_generation_timer", default=None
)


class GenerationTimer:
    def __init__(self) -> None:
        self.origin = time.perf_counter()
        self.marks: dict[str, int] = {}
        self._open: dict[str, float] = {}

    def start(self, name: str) -> None:
        self._open[name] = time.perf_counter()

    def stop(self, name: str) -> None:
        started = self._open.pop(name, None)
        if started is None:
            return
        self.marks[name] = int((time.perf_counter() - started) * 1000)

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        self.start(name)
        try:
            yield
        finally:
            self.stop(name)

    def total_ms(self) -> int:
        return int((time.perf_counter() - self.origin) * 1000)

    def as_dict(self) -> dict[str, int]:
        payload = dict(self.marks)
        payload["total_ms"] = self.total_ms()
        return payload


def current_timer() -> GenerationTimer | None:
    return _TIMER.get()


@contextmanager
def bind_timer(timer: GenerationTimer) -> Iterator[GenerationTimer]:
    token = _TIMER.set(timer)
    try:
        yield timer
    finally:
        _TIMER.reset(token)


@contextmanager
def span(name: str) -> Iterator[None]:
    timer = _TIMER.get()
    if timer is None:
        yield
        return
    with timer.span(name):
        yield


def log_generation_trace(
    *,
    timings: dict[str, int],
    model: str,
    prompt_version: str,
    attempts: int,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None,
    service_tier: str | None,
    reasoning_effort: str | None,
    trigger: str,
    requested_service_tier: str | None = None,
    generation_intent: str | None = None,
) -> None:
    logger.info(
        "GENERATION TRACE total=%sms database/context=%sms scheduler=%sms "
        "planner=%sms coach_protocol=%sms prompt/context=%sms openai=%sms "
        "validation=%sms persistence=%sms attempts=%s model=%s prompt=%s "
        "input_tokens=%s output_tokens=%s cached_input_tokens=%s "
        "intent=%s requested_service_tier=%s returned_service_tier=%s "
        "reasoning_effort=%s trigger=%s",
        timings.get("total_ms"),
        timings.get("context_build_ms"),
        timings.get("scheduler"),
        timings.get("planner"),
        timings.get("coach_protocol"),
        timings.get("prompt_context"),
        timings.get("provider_ms") or timings.get("openai"),
        timings.get("validation_ms"),
        timings.get("persistence_ms"),
        attempts,
        model,
        prompt_version,
        input_tokens,
        output_tokens,
        cached_input_tokens,
        generation_intent,
        requested_service_tier,
        service_tier,
        reasoning_effort,
        trigger,
    )
