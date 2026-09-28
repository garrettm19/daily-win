"""InstructionScheduler v1 — chooses which academic goal gets today's slot.

Deterministic. No LLM. Growth goals never consume an academic slot.
"""

from __future__ import annotations

from dataclasses import dataclass

from daily_win_api.domains.learning.academic import due_for_review
from daily_win_api.domains.learning.enums import AcademicBand
from daily_win_api.domains.learning.placement import (
    decide_placement,
    is_unknown,
    observed_weak,
)
from daily_win_api.domains.learning.taxonomy import (
    child_skills_for_parent,
    is_academic_code,
    is_generation_supported,
    is_growth_or_life_code,
    strand_code_for,
)

INSTRUCTION_SCHEDULER_V1 = "instruction_scheduler_v1"

# Priority #1 is the strongest preference, not a monopoly.
CONSECUTIVE_FOCUS_LIMIT = 3
MAX_GOAL_NEGLECT_WINDOW = 4
REMEDIATION_PREEMPT_CAP = 5
DIAGNOSTIC_PREEMPT_CAP = 2
REVIEW_LOAD_WINDOW = 3
REVIEW_LOAD_MAX = 1
REVIEW_COOLDOWN_WINS = 3

URGENCY_REMEDIATION = "active_remediation"
URGENCY_DIAGNOSTIC = "unresolved_diagnostic"
URGENCY_LEARNING = "active_learning"
URGENCY_REVIEW = "review_due"
URGENCY_MAINTENANCE = "maintenance"

_URGENCY_RANK = {
    URGENCY_REMEDIATION: 5,
    URGENCY_DIAGNOSTIC: 4,
    URGENCY_LEARNING: 3,
    URGENCY_REVIEW: 2,
    URGENCY_MAINTENANCE: 1,
}


@dataclass(frozen=True)
class ScheduledFocus:
    selected_goal_code: str
    selected_strand: str
    selection_reason_codes: tuple[str, ...]
    urgency_class: str
    recent_goal_history: tuple[str, ...]
    deferred_goals: tuple[str, ...]
    review_due: bool
    starvation_guard_triggered: bool
    scheduler_version: str = INSTRUCTION_SCHEDULER_V1
    why_selected: str = ""
    why_deferred: tuple[str, ...] = ()
    discovery_cycle: bool = False

    @property
    def allows_review(self) -> bool:
        return self.urgency_class in {URGENCY_REVIEW, URGENCY_MAINTENANCE}


@dataclass(frozen=True)
class _GoalView:
    code: str
    priority: int
    urgency: str
    never_selected: bool
    consecutive: int
    neglect: int


def schedule_instruction(data) -> ScheduledFocus:
    """Choose today's academic goal/strand. Planner chooses the skill."""
    from daily_win_api.domains.learning.planner import PlannerInput

    assert isinstance(data, PlannerInput)
    academic = [
        goal
        for goal in sorted(data.goals, key=lambda item: item.priority)
        if is_academic_code(goal.skill_code)
    ]
    if not academic:
        fallback = data.goals[0].skill_code if data.goals else "math.number_sense"
        return ScheduledFocus(
            selected_goal_code=fallback,
            selected_strand=fallback,
            selection_reason_codes=("no_academic_goal",),
            urgency_class=URGENCY_LEARNING,
            recent_goal_history=(),
            deferred_goals=(),
            review_due=False,
            starvation_guard_triggered=False,
            why_selected="No academic goal was active.",
        )
    history = _recent_goals(data)
    modes = data.recent_instruction_modes
    views = tuple(_view(goal, data, history) for goal in academic)
    review_load_high = _review_count(modes) > REVIEW_LOAD_MAX
    last_review_goal = next(
        (
            goal
            for goal, mode in zip(history, modes, strict=False)
            if mode == "review"
        ),
        None,
    )
    pick = _pick(
        views,
        review_load_high=review_load_high,
        last_review_goal=last_review_goal,
    )
    reasons = list(pick[1])
    selected = pick[0]
    starvation = "secondary_goal_starvation_guard" in reasons
    deferred = tuple(item.code for item in views if item.code != selected.code)
    why_deferred = tuple(
        _defer_reason(item, selected, review_load_high)
        for item in views
        if item.code != selected.code
    )
    return ScheduledFocus(
        selected_goal_code=selected.code,
        selected_strand=selected.code,
        selection_reason_codes=tuple(reasons),
        urgency_class=selected.urgency,
        recent_goal_history=history[:8],
        deferred_goals=deferred,
        review_due=selected.urgency == URGENCY_REVIEW,
        starvation_guard_triggered=starvation,
        why_selected=_why_selected(selected, reasons),
        why_deferred=why_deferred,
        discovery_cycle="discovery_cycle" in reasons,
    )


def _view(goal, data, history: tuple[str, ...]) -> _GoalView:
    urgency = classify_goal_urgency(goal.skill_code, data)
    consecutive = 0
    for code in history:
        if code == goal.skill_code:
            consecutive += 1
        else:
            break
    last_index = next(
        (index for index, code in enumerate(history) if code == goal.skill_code),
        None,
    )
    neglect = last_index if last_index is not None else len(history)
    never_selected = goal.skill_code not in history
    return _GoalView(
        code=goal.skill_code,
        priority=goal.priority,
        urgency=urgency,
        never_selected=never_selected,
        consecutive=consecutive,
        neglect=len(history) if never_selected else neglect,
    )


def classify_goal_urgency(goal_code: str, data) -> str:
    states = data.states
    age = data.age_years
    now = data.now
    placement = decide_placement(goal_code, age, states)
    candidates = _candidates(goal_code)
    snapshots = []
    for code in candidates:
        state = states.get(code)
        snapshots.append(state.academic if state else None)
    if any(item is not None and item.needs_remediation for item in snapshots):
        return URGENCY_REMEDIATION
    if any(observed_weak(item) for item in snapshots):
        return URGENCY_LEARNING
    if placement.sparse_evidence or all(is_unknown(item) for item in snapshots):
        return URGENCY_DIAGNOSTIC
    active_bands = {
        AcademicBand.EMERGING,
        AcademicBand.DEVELOPING,
        AcademicBand.NOT_OBSERVED,
    }
    if any(
        item is not None and item.band in active_bands for item in snapshots
    ) or any(item is None for item in snapshots):
        if not placement.sparse_evidence:
            return URGENCY_LEARNING
        return URGENCY_DIAGNOSTIC
    if any(item is not None and due_for_review(item, now=now) for item in snapshots):
        return URGENCY_REVIEW
    return URGENCY_MAINTENANCE


def _candidates(goal_code: str) -> list[str]:
    children = [
        str(item["code"])
        for item in child_skills_for_parent(goal_code)
        if is_generation_supported(str(item["code"]))
    ]
    if children:
        return children
    return [goal_code]


def _recent_goals(data) -> tuple[str, ...]:
    if data.recent_goal_codes:
        return data.recent_goal_codes
    return tuple(
        strand_code_for(code)
        for code in data.recent_skill_codes
        if is_academic_code(code)
    )


def _review_count(modes: tuple[str, ...]) -> int:
    window = modes[:REVIEW_LOAD_WINDOW]
    return sum(1 for mode in window if mode == "review")


def _pick(
    views: tuple[_GoalView, ...],
    *,
    review_load_high: bool,
    last_review_goal: str | None = None,
) -> tuple[_GoalView, tuple[str, ...]]:
    active = [
        item
        for item in views
        if item.urgency in {URGENCY_REMEDIATION, URGENCY_DIAGNOSTIC, URGENCY_LEARNING}
    ]
    reviewable = [item for item in views if item.urgency == URGENCY_REVIEW]
    maintenance = [item for item in views if item.urgency == URGENCY_MAINTENANCE]

    starved = [
        item
        for item in views
        if item.urgency in {URGENCY_REMEDIATION, URGENCY_DIAGNOSTIC, URGENCY_LEARNING}
        and item.neglect >= MAX_GOAL_NEGLECT_WINDOW
    ]
    new_unplaced = [
        item
        for item in views
        if item.never_selected
        and item.urgency in {URGENCY_DIAGNOSTIC, URGENCY_LEARNING, URGENCY_REMEDIATION}
    ]

    if starved:
        chosen = min(starved, key=lambda item: item.priority)
        reasons = _base_reasons(chosen)
        reasons.append("secondary_goal_starvation_guard")
        return chosen, tuple(reasons)

    discovery = _discovery_choice(views)
    if discovery is not None:
        return discovery

    if new_unplaced and active:
        current = _preferred(active)
        if current is not None and current.consecutive >= CONSECUTIVE_FOCUS_LIMIT:
            chosen = min(new_unplaced, key=lambda item: item.priority)
            reasons = _base_reasons(chosen)
            reasons.append("new_goal_needs_placement")
            return chosen, tuple(reasons)
        if current is None or current.urgency == URGENCY_MAINTENANCE:
            chosen = min(new_unplaced, key=lambda item: item.priority)
            reasons = _base_reasons(chosen)
            reasons.append("new_goal_needs_placement")
            return chosen, tuple(reasons)
        if new_unplaced[0].priority < (current.priority if current else 99):
            chosen = min(new_unplaced, key=lambda item: item.priority)
            reasons = _base_reasons(chosen)
            reasons.append("new_goal_needs_placement")
            return chosen, tuple(reasons)

    loaded_guard = False
    pool = active
    if not pool:
        pool = reviewable or maintenance or views
    if review_load_high and active:
        pool = active
        loaded_guard = True

    chosen = _preferred(pool)
    assert chosen is not None
    reasons = _base_reasons(chosen)
    rotated = _rotate_if_needed(chosen, views, review_load_high)
    if rotated is not None and rotated.code != chosen.code:
        chosen = rotated
        reasons = _base_reasons(chosen)
        reasons.append("consecutive_focus_limit")
    cooled = _avoid_review_ping_pong(chosen, reviewable, last_review_goal, active)
    if cooled is not None and cooled.code != chosen.code:
        chosen = cooled
        reasons = _base_reasons(chosen)
        reasons.append("review_cooldown")
    if loaded_guard:
        reasons.append("review_load_guard")
    if chosen.urgency == URGENCY_REVIEW:
        reasons.append("review_candidate")
    if chosen.urgency == URGENCY_MAINTENANCE:
        reasons.append("maintenance_only_candidate")
        reasons.append("no_active_learning_candidate")
    return chosen, tuple(reasons)


def _discovery_choice(
    views: tuple[_GoalView, ...],
) -> tuple[_GoalView, tuple[str, ...]] | None:
    diagnostic = [item for item in views if item.urgency == URGENCY_DIAGNOSTIC]
    if len(diagnostic) < 2:
        return None
    unsampled = [item for item in diagnostic if item.never_selected]
    if not unsampled:
        return None
    focused = [item for item in views if item.consecutive > 0]
    if not focused:
        return None
    current = focused[0]
    if current.consecutive < 1:
        return None
    chosen = min(unsampled, key=lambda item: item.priority)
    reasons = _base_reasons(chosen)
    reasons.append("discovery_cycle")
    return chosen, tuple(reasons)


def _preferred(pool: list[_GoalView]) -> _GoalView | None:
    if not pool:
        return None
    ranked = sorted(
        pool,
        key=lambda item: (-_URGENCY_RANK[item.urgency], item.priority),
    )
    return ranked[0]


def _avoid_review_ping_pong(
    chosen: _GoalView,
    reviewable: list[_GoalView],
    last_review_goal: str | None,
    active: list[_GoalView],
) -> _GoalView | None:
    if chosen.urgency != URGENCY_REVIEW:
        return None
    if last_review_goal != chosen.code:
        return None
    if active:
        return _preferred(active)
    alternatives = [item for item in reviewable if item.code != chosen.code]
    if not alternatives:
        return None
    return _preferred(alternatives)


def _rotate_if_needed(
    chosen: _GoalView,
    views: tuple[_GoalView, ...],
    review_load_high: bool,
) -> _GoalView | None:
    cap = CONSECUTIVE_FOCUS_LIMIT
    if chosen.urgency == URGENCY_REMEDIATION:
        cap = REMEDIATION_PREEMPT_CAP
    elif chosen.urgency == URGENCY_DIAGNOSTIC:
        cap = DIAGNOSTIC_PREEMPT_CAP
    if chosen.consecutive < cap:
        return None
    alternatives = [
        item
        for item in views
        if item.code != chosen.code
        and item.urgency in {URGENCY_REMEDIATION, URGENCY_DIAGNOSTIC, URGENCY_LEARNING}
    ]
    if not alternatives:
        if chosen.urgency in {URGENCY_REVIEW, URGENCY_MAINTENANCE} and (
            not review_load_high
        ):
            alternatives = [
                item
                for item in views
                if item.code != chosen.code and item.urgency == URGENCY_REVIEW
            ]
    if not alternatives:
        return None
    return min(
        alternatives,
        key=lambda item: (-_URGENCY_RANK[item.urgency], item.priority),
    )


def _base_reasons(chosen: _GoalView) -> list[str]:
    reasons = []
    if chosen.priority == 1:
        reasons.append("highest_priority")
    else:
        reasons.append("secondary_goal")
    if chosen.urgency == URGENCY_REMEDIATION:
        reasons.append("unresolved_learning")
        reasons.append("remediation_urgency")
    elif chosen.urgency == URGENCY_DIAGNOSTIC:
        reasons.append("unresolved_diagnostic")
    elif chosen.urgency == URGENCY_LEARNING:
        reasons.append("unresolved_learning")
    return reasons


def _why_selected(chosen: _GoalView, reasons: list[str]) -> str:
    name = chosen.code
    if "secondary_goal_starvation_guard" in reasons:
        return (
            f"Secondary goal {name} has not received an instructional "
            "opportunity recently."
        )
    if "discovery_cycle" in reasons:
        return (
            f"{name} is getting a first signal this week so no single "
            "academic area monopolizes discovery."
        )
    if "new_goal_needs_placement" in reasons:
        return f"{name} is a new active goal and still needs placement."
    if "consecutive_focus_limit" in reasons:
        return (
            f"{name} is eligible and the previous goal reached the "
            "consecutive-focus limit."
        )
    if chosen.urgency == URGENCY_REMEDIATION:
        return f"Recent evidence on {name} indicates a genuine weakness."
    if chosen.urgency == URGENCY_DIAGNOSTIC:
        return f"Placement for {name} is still uncertain."
    if chosen.urgency == URGENCY_REVIEW:
        return f"A retained skill in {name} is due for review."
    if chosen.urgency == URGENCY_MAINTENANCE:
        return f"No active-learning candidate remained; {name} is in maintenance."
    if chosen.priority == 1:
        return f"{name} is the highest-priority academic goal with unresolved learning."
    return f"{name} is an eligible academic goal."


def _defer_reason(
    item: _GoalView, selected: _GoalView, review_load_high: bool
) -> str:
    if item.urgency == URGENCY_MAINTENANCE:
        return f"{item.code}: retained and not currently due for review."
    if item.urgency == URGENCY_REVIEW and review_load_high:
        return (
            f"{item.code}: review deferred because recent Wins already "
            "include reviews."
        )
    if item.urgency == URGENCY_REVIEW:
        return f"{item.code}: review is due but {selected.code} has stronger urgency."
    if selected.urgency == URGENCY_REMEDIATION:
        return f"{item.code}: deferred while {selected.code} needs remediation."
    if selected.urgency == URGENCY_DIAGNOSTIC:
        return f"{item.code}: deferred while {selected.code} still needs placement."
    return f"{item.code}: recently practiced or lower scheduling preference."


def review_cooled(skill_code: str, data) -> bool:
    pairs = zip(
        data.recent_skill_codes[:REVIEW_COOLDOWN_WINS],
        data.recent_instruction_modes[:REVIEW_COOLDOWN_WINS],
        strict=False,
    )
    return any(skill == skill_code and mode == "review" for skill, mode in pairs)


def growth_overlay_code(data) -> str | None:
    growth = next(
        (
            goal
            for goal in sorted(data.goals, key=lambda item: item.priority)
            if is_growth_or_life_code(goal.skill_code)
        ),
        None,
    )
    return growth.skill_code if growth is not None else None
