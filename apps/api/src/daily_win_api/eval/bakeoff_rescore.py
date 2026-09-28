"""Offline rescoring of a stored Terra vs Luna bakeoff. No new provider calls."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import DailyWinDraft, DailyWinGenerationResult
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL
from daily_win_api.eval.attribution import (
    FailureOwner,
    original_safety_was_false_positive,
)
from daily_win_api.eval.bakeoff import (
    BAKEOFF_MODELS,
    LUNA,
    TERRA,
    CallRecord,
    _recommend,
    _review_markdown,
    _score_call,
    _summarize,
    load_bakeoff_cases,
)
from daily_win_api.eval.pricing import pricing_catalog
from daily_win_api.eval.scoring import write_results

ORIGINAL_BAKEOFF = (
    Path(__file__).resolve().parents[3]
    / "eval-results"
    / "20260919T211946Z-terra-luna.json"
)


def rescore_terra_luna_artifact(
    source: Path | None = None,
    *,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    path = source or ORIGINAL_BAKEOFF
    if not path.exists():
        raise SystemExit(
            f"Original bakeoff artifact is missing: {path}. "
            "No new live calls were made."
        )
    original = json.loads(path.read_text(encoding="utf-8"))
    cases_by_id = {item.id: item for item in load_bakeoff_cases()}
    case_rows: list[dict[str, Any]] = []
    call_rows: list[CallRecord] = []
    missing: list[str] = []
    for stored in original.get("cases", []):
        case_id = stored["id"]
        live_case = cases_by_id.get(case_id)
        if live_case is None:
            missing.append(f"{case_id}: unknown case")
            continue
        outputs: dict[str, Any] = {}
        for model in BAKEOFF_MODELS:
            stored_out = (stored.get("outputs") or {}).get(model) or {}
            draft_payload = stored_out.get("draft")
            if draft_payload is None:
                missing.append(f"{case_id}/{model}: draft missing")
                continue
            draft = DailyWinDraft.model_validate(draft_payload)
            generated = DailyWinGenerationResult(
                draft=draft,
                provider="openai",
                model=model,
                prompt_version=stored_out.get("prompt_version") or PROMPT_VERSION,
                input_tokens=stored_out.get("input_tokens"),
                output_tokens=stored_out.get("output_tokens"),
                total_tokens=stored_out.get("total_tokens"),
                latency_ms=stored_out.get("latency_ms"),
            )
            record = _score_call(
                live_case,
                generated,
                attempts=int(stored_out.get("attempts") or 1),
                retry_reason=stored_out.get("retry_reason"),
            )
            payload = asdict(record)
            original_hard = list(stored_out.get("hard_failures") or [])
            payload["original_hard_failures"] = original_hard
            if original_safety_was_false_positive(
                original_hard_failures=original_hard,
                current_safety_ok=bool(record.deterministic_safety),
            ):
                payload["original_failure_owner"] = (
                    FailureOwner.APPLICATION_VALIDATOR_FALSE_POSITIVE.value
                )
            else:
                payload["original_failure_owner"] = stored_out.get("failure_owner")
            outputs[model] = payload
            call_rows.append(record)
        case_rows.append(
            {
                "id": stored["id"],
                "coverage": stored["coverage"],
                "golden_id": stored.get("golden_id"),
                "profile_summary": stored["profile_summary"],
                "plan_summary": stored["plan_summary"],
                "instruction_plan": stored["instruction_plan"],
                "context_sha256": stored.get("context_sha256"),
                "privacy_ok": True,
                "synthetic": True,
                "store": False,
                "prompt_version": PROMPT_VERSION,
                "outputs": outputs,
            }
        )
    if missing:
        raise SystemExit(
            "Cannot rescore without stored drafts; no new live calls. Missing: "
            + "; ".join(missing)
        )

    summary = _summarize(call_rows)
    created_at = datetime.now(UTC)
    payload = {
        "created_at": created_at.isoformat(),
        "live": True,
        "rescored": True,
        "new_live_calls": 0,
        "source_artifact": path.name,
        "bakeoff": "terra-luna",
        "prompt_version": PROMPT_VERSION,
        "models": list(BAKEOFF_MODELS),
        "baseline_model": DEFAULT_OPENAI_MODEL,
        "production_default_unchanged": DEFAULT_OPENAI_MODEL == TERRA,
        "routing_implemented": False,
        "calls_attempted": original.get("calls_attempted"),
        "calls_succeeded": original.get("calls_succeeded"),
        "calls_retried": original.get("calls_retried"),
        "case_count": len(case_rows),
        "privacy": original.get("privacy"),
        "pricing": pricing_catalog(),
        "note": (
            "Corrected offline rescore of stored drafts. Not canonical learner "
            "memory. Original artifact preserved for audit."
        ),
        "summary": summary,
        "recommendation": _recommend(summary, live=True),
        "luna_case_5": _luna_case_5_note(case_rows),
        "cases": case_rows,
    }
    directory = output_dir or path.parent
    json_path = directory / "20260919T211946Z-terra-luna-v034a.json"
    review_path = directory / "20260919T211946Z-terra-luna-v034a-review.md"
    cases = tuple(cases_by_id[row["id"]] for row in case_rows)
    write_results(json_path, payload)
    review_path.write_text(_review_markdown(cases, case_rows), encoding="utf-8")
    return {"json": json_path, "review": review_path, "source": path}


def _luna_case_5_note(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = next(item for item in case_rows if item["id"] == "case_5_age9_comprehension")
    luna = row["outputs"][LUNA]
    return {
        "current_safety_ok": luna["deterministic_safety"],
        "model_quality_hard_failures": luna["model_quality_hard_failures"],
        "original_hard_failures": luna.get("original_hard_failures"),
        "original_failure_owner": luna.get("original_failure_owner"),
        "production_would_reject": luna["production_would_reject"],
        "note": (
            "If current_safety_ok is true, the original unsafe_content mark "
            "was an application-validator false positive on ordinary 'matches'."
        ),
    }
