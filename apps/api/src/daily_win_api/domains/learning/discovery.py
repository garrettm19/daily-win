"""Discovery week progress. Works with placement_policy_v1 and scheduler v1."""

from __future__ import annotations

from daily_win_api.domains.learning.placement import is_unknown
from daily_win_api.domains.learning.taxonomy import is_academic_code

DISCOVERY_HEADLINE = "This week: getting to know how they learn"
DISCOVERY_BODY = "These first Wins help Daily Win find the right level."


def discovery_is_active(goals: tuple[str, ...], states: dict) -> bool:
    academic = [code for code in goals if is_academic_code(code)]
    if len(academic) < 2:
        return False
    unknown = 0
    for code in academic:
        state = states.get(code)
        academic_state = getattr(state, "academic", None) if state is not None else None
        if academic_state is None or is_unknown(academic_state):
            unknown += 1
        else:
            children_unknown = True
            for key, item in states.items():
                if not str(key).startswith(code.split(".")[0] + "."):
                    continue
                snap = getattr(item, "academic", None)
                if snap is not None and not is_unknown(snap):
                    children_unknown = False
                    break
            if children_unknown and academic_state is None:
                unknown += 1
    return unknown >= 1


def discovery_domain_status(
    goals: tuple[str, ...], sampled_domains: tuple[str, ...]
) -> list[dict[str, str]]:
    wanted = []
    for code in goals:
        if not is_academic_code(code):
            continue
        domain = _domain(code)
        if domain not in wanted:
            wanted.append(domain)
    rows = []
    for domain in wanted:
        collected = domain.lower() in {item.lower() for item in sampled_domains}
        rows.append(
            {
                "domain": domain,
                "status": "first_signal_collected" if collected else "still_to_explore",
                "label": (
                    f"{domain} — first signal collected"
                    if collected
                    else f"{domain} — still to explore"
                ),
            }
        )
    return rows


def _domain(code: str) -> str:
    prefix = code.split(".", 1)[0]
    return {"math": "Math", "writing": "Writing", "reading": "Reading"}.get(
        prefix, prefix.title()
    )
