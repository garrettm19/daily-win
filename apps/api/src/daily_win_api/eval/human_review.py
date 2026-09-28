"""Blinded human-review template and score aggregation. Not learner data."""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

from daily_win_api.ai.prompts.current import PROMPT_VERSION

REVIEW_SCORE_KEYS = (
    ("educational_usefulness", "Educational usefulness"),
    ("plan_fidelity", "Plan fidelity"),
    ("age_appropriateness", "Age appropriateness"),
    ("parent_clarity", "Parent clarity"),
    ("engagement", "Engagement"),
    ("assessment_quality", "Assessment quality"),
    ("coaching_quality", "Coaching quality"),
    ("overall", "Overall"),
)

_CASE_HEADER = re.compile(r"^## Case (\d+) — (.+)$", re.MULTILINE)
_NOTE_LINE = re.compile(r"^Note:\s*(.*)$", re.MULTILINE)


def review_score_template() -> list[str]:
    lines = ["### Scores", ""]
    for _key, label in REVIEW_SCORE_KEYS:
        lines.append(f"{label}: A= _ B= _")
    lines.extend(
        [
            "Preference: _",
            "Would use with my child: _",
            "Verdict A: _",
            "Verdict B: _",
            "Note:",
            "",
        ]
    )
    return lines


def parse_review_markdown(markdown: str) -> list[dict[str, Any]]:
    headers = list(_CASE_HEADER.finditer(markdown))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(headers):
        start = match.start()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(markdown)
        block = markdown[start:end]
        scores_a: dict[str, int | None] = {}
        scores_b: dict[str, int | None] = {}
        for key, label in REVIEW_SCORE_KEYS:
            scores_a[key] = None
            scores_b[key] = None
            found = re.search(
                rf"^{re.escape(label)}:\s*A=\s*(\d|_)\s+B=\s*(\d|_)\s*$",
                block,
                re.MULTILINE,
            )
            if found:
                scores_a[key] = _as_score(found.group(1))
                scores_b[key] = _as_score(found.group(2))
        fields = {
            item.group(1): item.group(2).strip()
            for item in re.finditer(
                r"^(Preference|Would use with my child|"
                r"Verdict A|Verdict B):\s*(.+?)\s*$",
                block,
                re.MULTILINE,
            )
        }
        note_match = _NOTE_LINE.search(block)
        rows.append(
            {
                "case_number": int(match.group(1)),
                "coverage": match.group(2).strip(),
                "scores_a": scores_a,
                "scores_b": scores_b,
                "preference": _clean_choice(fields.get("Preference")),
                "would_use": _clean_choice(fields.get("Would use with my child")),
                "verdict_a": _clean_choice(fields.get("Verdict A")),
                "verdict_b": _clean_choice(fields.get("Verdict B")),
                "note": (note_match.group(1).strip() if note_match else ""),
                "complete": _case_complete(scores_a, scores_b, fields),
            }
        )
    return rows


def summarize_human_review(markdown: str, reveal: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_review_markdown(markdown)
    assignment = reveal.get("assignment") or {}
    completed = [row for row in parsed if row["complete"]]
    by_model: dict[str, dict[str, list[int]]] = {}
    pairwise = {"A": 0, "B": 0, "Tie": 0}
    would_use = {"A": 0, "B": 0, "Both": 0, "Neither": 0}
    verdicts: dict[str, dict[str, int]] = {}
    for row in completed:
        mapping = assignment.get(f"case_{row['case_number']}", {})
        a_model = mapping.get("A")
        b_model = mapping.get("B")
        if not a_model or not b_model:
            continue
        for key, _label in REVIEW_SCORE_KEYS:
            _append_score(by_model, a_model, key, row["scores_a"][key])
            _append_score(by_model, b_model, key, row["scores_b"][key])
        pref = row["preference"]
        if pref in pairwise:
            pairwise[pref] += 1
        use = row["would_use"]
        if use in would_use:
            would_use[use] += 1
        for arm, model in (("verdict_a", a_model), ("verdict_b", b_model)):
            verdicts.setdefault(model, {"PASS": 0, "NEEDS REVISION": 0})
            value = row[arm]
            if value in {"PASS", "NEEDS REVISION"}:
                verdicts[model][value] += 1
    averages = {
        model: {
            key: (statistics.mean(values) if values else None)
            for key, values in scores.items()
        }
        for model, scores in by_model.items()
    }
    pairwise_models = _pairwise_by_model(completed, assignment)
    return {
        "exploratory": True,
        "n_cases": len(parsed),
        "n_scored": len(completed),
        "complete": len(completed) == len(parsed) and bool(parsed),
        "prompt_version": PROMPT_VERSION,
        "note": (
            "Exploratory human review, n=8. Not statistical significance. "
            "Not learner data."
        ),
        "average_by_model": averages,
        "pairwise_preference": pairwise,
        "pairwise_wins_by_model": pairwise_models,
        "would_use": would_use,
        "verdicts_by_model": verdicts,
        "category_differences": _category_differences(averages),
        "cases": parsed,
    }


def load_reveal(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_score(raw: str) -> int | None:
    if raw == "_":
        return None
    value = int(raw)
    if 1 <= value <= 5:
        return value
    return None


def _clean_choice(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip().strip("_").strip()
    return value or None


def _case_complete(
    scores_a: dict[str, int | None],
    scores_b: dict[str, int | None],
    fields: dict[str, str],
) -> bool:
    if any(value is None for value in scores_a.values()):
        return False
    if any(value is None for value in scores_b.values()):
        return False
    preference = _clean_choice(fields.get("Preference"))
    would_use = _clean_choice(fields.get("Would use with my child"))
    verdict_a = _clean_choice(fields.get("Verdict A"))
    verdict_b = _clean_choice(fields.get("Verdict B"))
    return bool(preference and would_use and verdict_a and verdict_b)


def _append_score(
    store: dict[str, dict[str, list[int]]],
    model: str,
    key: str,
    value: int | None,
) -> None:
    if value is None:
        return
    store.setdefault(model, {}).setdefault(key, []).append(value)


def _pairwise_by_model(
    completed: list[dict[str, Any]], assignment: dict[str, Any]
) -> dict[str, int]:
    wins: dict[str, int] = {}
    for row in completed:
        mapping = assignment.get(f"case_{row['case_number']}", {})
        pref = row["preference"]
        if pref == "Tie":
            wins["tie"] = wins.get("tie", 0) + 1
            continue
        model = mapping.get(pref)
        if model:
            wins[model] = wins.get(model, 0) + 1
    return wins


def _category_differences(
    averages: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    models = list(averages)
    if len(models) != 2:
        return {}
    left, right = models
    diffs = {}
    for key, _label in REVIEW_SCORE_KEYS:
        a = averages[left].get(key)
        b = averages[right].get(key)
        if a is None or b is None:
            diffs[key] = None
        else:
            diffs[key] = {left: a, right: b, "delta": a - b}
    return diffs
