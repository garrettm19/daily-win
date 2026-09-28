"""Deterministic weekly learning synthesis. Rebuildable. Not an LLM biography."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from daily_win_api.domains.learning.taxonomy import (
    definition_by_code,
    is_academic_code,
    strand_code_for,
)

WEEKLY_SUMMARY_V1 = "weekly_summary_v1"

BANNED_WEEKLY_CLAIMS = (
    "math kid",
    "bad writer",
    "lazy",
    "low grit",
    "natural athlete",
    "visual learner",
    "kinesthetic learner",
    "naturally gifted",
    "learns best visually",
    "dumb",
    "smart kid",
    "top 1%",
    "2x learning",
    "alpha at home",
)

_DOMAIN = {
    "math": "Math",
    "writing": "Writing",
    "reading": "Reading",
    "growth": "Growth",
    "life": "Life skills",
}

_INDEPENDENT = frozenset({"correct_independently"})
_SUPPORTED = frozenset(
    {"correct_after_light_prompt", "correct_after_significant_help"}
)
_HARD = frozenset({"incorrect", "not_attempted", "correct_after_significant_help"})


@dataclass(frozen=True)
class SessionEvidence:
    skill_code: str
    instruction_mode: str
    academic_result: str | None = None
    difficulty: str | None = None
    engagement: str | None = None
    completion: str | None = None
    setback_response: str | None = None
    self_correction: str | None = None
    strategy: str | None = None
    performance_effort: str | None = None
    notice_chips: tuple[str, ...] = ()
    bonus_category: str | None = None
    bonus_engagement: str | None = None
    non_target_error: str | None = None
    source_keys: tuple[str, ...] = ()
    teach_the_coach: bool = False
    personal_best: bool = False


@dataclass(frozen=True)
class EmergingNeedSignal:
    hint: str
    observation_count: int
    recommendation: str
    claim: str


@dataclass(frozen=True)
class EngagementMemory:
    recently_enjoyed: tuple[str, ...]
    recently_low: tuple[str, ...]
    low_engagement_categories: tuple[str, ...]


@dataclass(frozen=True)
class NextWeekPreview:
    primary_academic_focus: str
    secondary_academic_focus: str | None
    growth_focus: str | None
    why: str
    scheduled_goal: str | None = None


@dataclass(frozen=True)
class WeeklyLearningSummary:
    week_start: str
    week_end: str
    summary_version: str
    source_session_count: int
    source_keys: tuple[str, ...]
    wins_completed: int
    academic_areas: tuple[str, ...]
    what_looked_strong: tuple[str, ...]
    what_still_took_work: tuple[str, ...]
    how_they_handled_challenge: tuple[str, ...]
    what_they_enjoyed: tuple[str, ...]
    what_changes_next_week: tuple[str, ...]
    parent_coaching_suggestion: str
    win_of_the_week_candidates: tuple[str, ...]
    emerging_needs: tuple[EmergingNeedSignal, ...]
    engagement_memory: EngagementMemory
    next_week: NextWeekPreview | None
    discovery_progress: tuple[str, ...]
    claims_trace: tuple[tuple[str, str], ...]
    policy_versions: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "summary_version": self.summary_version,
            "source_session_count": self.source_session_count,
            "source_keys": list(self.source_keys),
            "this_week": {
                "wins_completed": self.wins_completed,
                "academic_areas": list(self.academic_areas),
            },
            "what_looked_strong": list(self.what_looked_strong),
            "what_still_took_work": list(self.what_still_took_work),
            "how_they_handled_challenge": list(self.how_they_handled_challenge),
            "what_they_enjoyed": list(self.what_they_enjoyed),
            "what_changes_next_week": list(self.what_changes_next_week),
            "one_thing_for_the_parent": self.parent_coaching_suggestion,
            "win_of_the_week_candidates": list(self.win_of_the_week_candidates),
            "emerging_needs": [
                {
                    "hint": item.hint,
                    "observation_count": item.observation_count,
                    "recommendation": item.recommendation,
                    "claim": item.claim,
                }
                for item in self.emerging_needs
            ],
            "engagement_memory": {
                "recently_enjoyed": list(self.engagement_memory.recently_enjoyed),
                "recently_low": list(self.engagement_memory.recently_low),
                "low_engagement_categories": list(
                    self.engagement_memory.low_engagement_categories
                ),
            },
            "next_week": (
                None
                if self.next_week is None
                else {
                    "primary_academic_focus": self.next_week.primary_academic_focus,
                    "secondary_academic_focus": self.next_week.secondary_academic_focus,
                    "growth_focus": self.next_week.growth_focus,
                    "why": self.next_week.why,
                    "scheduled_goal": self.next_week.scheduled_goal,
                }
            ),
            "discovery_progress": list(self.discovery_progress),
            "claims_trace": [
                {"claim": claim, "source": source}
                for claim, source in self.claims_trace
            ],
            "policy_versions": dict(self.policy_versions),
        }


def synthesize_week(
    sessions: tuple[SessionEvidence, ...],
    *,
    week_start: datetime,
    week_end: datetime,
    next_week: NextWeekPreview | None = None,
    policy_versions: dict[str, str] | None = None,
) -> WeeklyLearningSummary:
    academic = [item for item in sessions if is_academic_code(item.skill_code)]
    areas = tuple(
        dict.fromkeys(_area_label(item.skill_code) for item in academic)
    )
    strong, strong_trace = _strong_claims(academic)
    weak, weak_trace = _work_claims(academic)
    challenge, challenge_trace = _challenge_claims(sessions)
    enjoyed, enjoyed_trace = _enjoyed_claims(sessions)
    emerging = emerging_need_signals(sessions)
    memory = engagement_memory(sessions)
    changes = _next_week_changes(weak, strong, next_week)
    traces = strong_trace + weak_trace + challenge_trace + enjoyed_trace
    keys = tuple(
        key for item in sessions for key in item.source_keys
    ) or tuple(f"session-{index}" for index, _item in enumerate(sessions))
    return WeeklyLearningSummary(
        week_start=week_start.date().isoformat(),
        week_end=week_end.date().isoformat(),
        summary_version=WEEKLY_SUMMARY_V1,
        source_session_count=len(sessions),
        source_keys=keys,
        wins_completed=len(sessions),
        academic_areas=areas,
        what_looked_strong=strong,
        what_still_took_work=weak,
        how_they_handled_challenge=challenge,
        what_they_enjoyed=enjoyed,
        what_changes_next_week=changes,
        parent_coaching_suggestion=parent_coaching_suggestion(sessions),
        win_of_the_week_candidates=_win_candidates(sessions),
        emerging_needs=emerging,
        engagement_memory=memory,
        next_week=next_week,
        discovery_progress=discovery_progress_lines(sessions),
        claims_trace=traces,
        policy_versions=policy_versions
        or {
            "summary_version": WEEKLY_SUMMARY_V1,
            "coach_protocol": "coach_protocol_v1",
            "scheduler": "instruction_scheduler_v1",
        },
    )


def parent_coaching_suggestion(sessions: tuple[SessionEvidence, ...]) -> str:
    if any(
        item.instruction_mode == "diagnostic"
        and item.academic_result == "correct_after_significant_help"
        for item in sessions
    ):
        return "On diagnostics, avoid teaching before the check."
    if sum(
        1
        for item in sessions
        if item.setback_response == "needed_significant_help"
    ) >= 2:
        return "Ask them to explain the strategy before correcting the answer."
    if any(item.self_correction == "self_corrected" for item in sessions):
        return "If they catch an error, pause and let them finish the fix."
    if any(item.setback_response == "stopped_or_avoided" for item in sessions):
        return (
            "If they disengage, shorten the activity and keep dignity. "
            "Tomorrow can adapt."
        )
    if any(item.teach_the_coach for item in sessions):
        return "Ask them to explain the strategy before stepping in."
    return "If they are thinking, wait before giving the first hint."


def engagement_memory(sessions: tuple[SessionEvidence, ...]) -> EngagementMemory:
    enjoyed: list[str] = []
    low: list[str] = []
    low_categories: list[str] = []
    counts: dict[str, int] = {}
    for item in sessions:
        label = _mechanic_label(item)
        if (
            item.bonus_engagement in {"loved_it", "liked_it"}
            or item.engagement == "high"
        ):
            if label not in enjoyed:
                enjoyed.append(label)
        if item.bonus_engagement == "not_into_it":
            counts[item.bonus_category or label] = (
                counts.get(item.bonus_category or label, 0) + 1
            )
            if label not in low:
                low.append(label)
    for category, count in counts.items():
        if count >= 2 and category not in low_categories:
            low_categories.append(category)
    return EngagementMemory(
        recently_enjoyed=tuple(enjoyed[:4]),
        recently_low=tuple(low[:4]),
        low_engagement_categories=tuple(low_categories),
    )


def emerging_need_signals(
    sessions: tuple[SessionEvidence, ...]
) -> tuple[EmergingNeedSignal, ...]:
    counts: dict[str, int] = {}
    for item in sessions:
        hint = item.non_target_error
        if not hint:
            continue
        counts[hint] = counts.get(hint, 0) + 1
    signals = []
    for hint, count in sorted(counts.items()):
        if count < 3:
            continue
        signals.append(
            EmergingNeedSignal(
                hint=hint,
                observation_count=count,
                recommendation="consider_diagnostic",
                claim=(
                    f"Parent observations mentioned {hint} {count} times. "
                    "Consider a diagnostic before changing academic state."
                ),
            )
        )
    return tuple(signals)


def discovery_progress_lines(sessions: tuple[SessionEvidence, ...]) -> tuple[str, ...]:
    seen: dict[str, bool] = {"Math": False, "Writing": False, "Reading": False}
    for item in sessions:
        area = _area_label(item.skill_code)
        if area in seen and item.academic_result:
            seen[area] = True
    lines = []
    for area, collected in seen.items():
        if collected:
            lines.append(f"{area} — first signal collected")
        else:
            lines.append(f"{area} — still to explore")
    return tuple(lines)


def weekly_text_is_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(item in lowered for item in BANNED_WEEKLY_CLAIMS)


def _strong_claims(
    academic: list[SessionEvidence],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    claims: list[str] = []
    traces: list[tuple[str, str]] = []
    independent = [
        item for item in academic if item.academic_result in _INDEPENDENT
    ]
    if independent:
        areas = sorted({_area_label(item.skill_code) for item in independent})
        claim = (
            f"{len(independent)} academic check"
            f"{'s' if len(independent) != 1 else ''} "
            f"completed independently ({', '.join(areas)})."
        )
        claims.append(claim)
        traces.append((claim, "measurement:correct_independently"))
    self_fixed = [
        item for item in academic if item.self_correction == "self_corrected"
    ]
    if self_fixed:
        claim = (
            f"They independently corrected an error in {len(self_fixed)} "
            "activit"
            f"{'ies' if len(self_fixed) != 1 else 'y'}."
        )
        claims.append(claim)
        traces.append((claim, "observation:self_corrected"))
    automatic = [
        item for item in academic if item.performance_effort == "automatic"
    ]
    if automatic:
        areas = sorted({_area_label(item.skill_code) for item in automatic})
        claim = f"{areas[0]} looked relatively automatic this week."
        claims.append(claim)
        traces.append((claim, "observation:performance_effort"))
    explained = [item for item in academic if item.teach_the_coach]
    if explained:
        claim = "They explained how they solved a task to the coach."
        claims.append(claim)
        traces.append((claim, "observation:teach_the_coach"))
    if not claims:
        claims.append(
            "Not enough independent academic evidence yet to name a strength."
        )
        traces.append((claims[0], "insufficient_evidence"))
    return tuple(claims), tuple(traces)


def _work_claims(
    academic: list[SessionEvidence],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    claims: list[str] = []
    traces: list[tuple[str, str]] = []
    supported = [item for item in academic if item.academic_result in _SUPPORTED]
    hard = [item for item in academic if item.academic_result in _HARD]
    by_area: dict[str, list[SessionEvidence]] = {}
    for item in academic:
        by_area.setdefault(_area_label(item.skill_code), []).append(item)
    effortful = [
        item
        for item in academic
        if item.performance_effort
        in {"effortful_but_independent", "effortful_with_support"}
    ]
    if supported or hard:
        areas = sorted(
            {
                _area_label(item.skill_code)
                for item in supported + hard
            }
        )
        claim = f"{' and '.join(areas)} still required more support."
        claims.append(claim)
        traces.append((claim, "measurement:supported_or_incorrect"))
    if effortful:
        areas = sorted({_area_label(item.skill_code) for item in effortful})
        claim = f"{areas[0]} still looked effortful."
        claims.append(claim)
        traces.append((claim, "observation:performance_effort"))
    if len(by_area) >= 2:
        independence = {
            area: sum(1 for item in rows if item.academic_result in _INDEPENDENT)
            for area, rows in by_area.items()
        }
        ranked = sorted(independence.items(), key=lambda pair: pair[1], reverse=True)
        if ranked[0][1] > ranked[-1][1]:
            claim = (
                f"{ranked[0][0]} required less support than {ranked[-1][0]} "
                "in this week's Daily Wins."
            )
            claims.append(claim)
            traces.append((claim, "derived:relative_support"))
    if not claims:
        claims.append("No repeated support pattern stood out this week.")
        traces.append((claims[0], "insufficient_evidence"))
    return tuple(claims), tuple(traces)


def _challenge_claims(
    sessions: tuple[SessionEvidence, ...],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    claims: list[str] = []
    traces: list[tuple[str, str]] = []
    continued = [
        item
        for item in sessions
        if item.setback_response == "continued_after_prompt"
    ]
    independent = [
        item
        for item in sessions
        if item.setback_response == "kept_going_independently"
    ]
    disengaged = [
        item
        for item in sessions
        if item.setback_response == "stopped_or_avoided"
    ]
    if independent:
        claim = (
            f"They independently retried after a setback in {len(independent)} "
            "challenge"
            f"{'s' if len(independent) != 1 else ''}."
        )
        claims.append(claim)
        traces.append((claim, "observation:setback"))
    if continued:
        claim = (
            f"They continued after one prompt in {len(continued)} challenge"
            f"{'s' if len(continued) != 1 else ''}."
        )
        claims.append(claim)
        traces.append((claim, "observation:setback"))
    if disengaged:
        claim = (
            f"They disengaged after repeated difficulty in {len(disengaged)} "
            "session"
            f"{'s' if len(disengaged) != 1 else ''}."
        )
        claims.append(claim)
        traces.append((claim, "observation:setback"))
    if not claims:
        claims.append("No setback was reported this week.")
        traces.append((claims[0], "observation:no_setback"))
    return tuple(claims), tuple(traces)


def _enjoyed_claims(
    sessions: tuple[SessionEvidence, ...],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    claims: list[str] = []
    traces: list[tuple[str, str]] = []
    loved = [
        item
        for item in sessions
        if item.bonus_engagement in {"loved_it", "liked_it"}
    ]
    disliked = [
        item for item in sessions if item.bonus_engagement == "not_into_it"
    ]
    if loved:
        labels = sorted({_mechanic_label(item) for item in loved})
        claim = f"They enjoyed {', '.join(labels)}."
        claims.append(claim)
        traces.append((claim, "preference:bonus_engagement"))
    counts: dict[str, int] = {}
    for item in disliked:
        key = item.bonus_category or _mechanic_label(item)
        counts[key] = counts.get(key, 0) + 1
    for category, count in counts.items():
        if count >= 2:
            claim = f"They rated the {category} challenge low-engagement twice."
            claims.append(claim)
            traces.append((claim, "preference:bonus_engagement"))
    if not claims:
        claims.append("No explicit activity reaction was recorded this week.")
        traces.append((claims[0], "insufficient_preference_evidence"))
    return tuple(claims), tuple(traces)


def _next_week_changes(
    weak: tuple[str, ...],
    strong: tuple[str, ...],
    next_week: NextWeekPreview | None,
) -> tuple[str, ...]:
    if next_week is not None:
        return (next_week.why,)
    if weak and "insufficient" not in weak[0].lower():
        return (weak[0],)
    if strong:
        return ("Keep gathering independent evidence on the current targets.",)
    return ("Continue the current instructional plan.",)


def _win_candidates(sessions: tuple[SessionEvidence, ...]) -> tuple[str, ...]:
    candidates: list[str] = []
    if any(item.self_correction == "self_corrected" for item in sessions):
        candidates.append("Fixed their own work")
    if any(item.academic_result == "correct_independently" for item in sessions):
        candidates.append("Solved a challenge independently")
    if any(item.setback_response == "kept_going_independently" for item in sessions):
        candidates.append("Kept going after getting stuck")
    if any(item.teach_the_coach for item in sessions):
        candidates.append("Explained something clearly")
    if any(item.personal_best for item in sessions):
        candidates.append("Beat a personal record")
    return tuple(candidates)


def _area_label(skill_code: str) -> str:
    prefix = skill_code.split(".", 1)[0]
    return _DOMAIN.get(prefix, prefix.title())


def _mechanic_label(item: SessionEvidence) -> str:
    if item.bonus_category:
        return item.bonus_category.replace("_", " ")
    return _area_label(item.skill_code).lower() + " challenges"


def skill_display(skill_code: str) -> str:
    item = definition_by_code().get(skill_code)
    if item is None:
        return strand_code_for(skill_code)
    return str(item["display_name"])
