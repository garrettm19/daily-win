"""Operational model-price metadata for eval estimates.

These are comparison rates, not invoices. They can change; do not scatter
them through scoring or bakeoff code. Last verified against official OpenAI
model pages where dated.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

PRICING_LAST_VERIFIED = date(2026, 9, 19)


@dataclass(frozen=True)
class ModelPrice:
    model: str
    input_usd_per_million: float
    output_usd_per_million: float
    last_verified_date: date | None
    notes: str = ""


# Source of truth for eval cost estimates. Update here when OpenAI list prices
# change; then re-score stored token counts instead of re-running live calls.
OPENAI_MODEL_PRICES: dict[str, ModelPrice] = {
    "gpt-5.6-terra": ModelPrice(
        model="gpt-5.6-terra",
        input_usd_per_million=2.00,
        output_usd_per_million=12.00,
        last_verified_date=PRICING_LAST_VERIFIED,
        notes="Official OpenAI model page as of 2026-09-19.",
    ),
    "gpt-5.6-luna": ModelPrice(
        model="gpt-5.6-luna",
        input_usd_per_million=0.20,
        output_usd_per_million=1.20,
        last_verified_date=PRICING_LAST_VERIFIED,
        notes="Official OpenAI model page as of 2026-09-19.",
    ),
    "gpt-5.6-sol": ModelPrice(
        model="gpt-5.6-sol",
        input_usd_per_million=10.00,
        output_usd_per_million=40.00,
        last_verified_date=None,
        notes="Not re-verified in V0.3.4a. Comparison placeholder only.",
    ),
}


@dataclass(frozen=True)
class CostEstimate:
    total_usd: float
    input_usd: float
    output_usd: float
    output_share: float


def price_for(model: str) -> ModelPrice | None:
    return OPENAI_MODEL_PRICES.get(model)


def estimate_cost_usd(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    parts = estimate_cost_parts(model, input_tokens, output_tokens)
    return None if parts is None else parts.total_usd


def estimate_cost_parts(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> CostEstimate | None:
    price = price_for(model)
    if price is None or input_tokens is None or output_tokens is None:
        return None
    input_usd = (input_tokens / 1_000_000) * price.input_usd_per_million
    output_usd = (output_tokens / 1_000_000) * price.output_usd_per_million
    total = input_usd + output_usd
    share = 0.0 if total == 0 else output_usd / total
    return CostEstimate(
        total_usd=total,
        input_usd=input_usd,
        output_usd=output_usd,
        output_share=share,
    )


def pricing_catalog() -> list[dict[str, Any]]:
    rows = []
    for price in OPENAI_MODEL_PRICES.values():
        rows.append(
            {
                "model": price.model,
                "input_usd_per_million": price.input_usd_per_million,
                "output_usd_per_million": price.output_usd_per_million,
                "last_verified_date": (
                    None
                    if price.last_verified_date is None
                    else price.last_verified_date.isoformat()
                ),
                "notes": price.notes,
            }
        )
    return rows
