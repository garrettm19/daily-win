"""Deterministic educational explanations. No LLM. No chain-of-thought."""

from __future__ import annotations

from daily_win_api.domains.learning.academic import due_for_review
from daily_win_api.domains.learning.enums import AcademicBand, ScaffoldLevel
from daily_win_api.domains.learning.observatory_schemas import WhyNotTrace
from daily_win_api.domains.learning.planner import InstructionPlan, PlannerInput
from daily_win_api.domains.learning.prerequisites import (
    dependents_for,
    prerequisites_for,
)
from daily_win_api.domains.learning.taxonomy import definition_by_code, is_academic_code

_SCAFFOLD_RANK = {
    ScaffoldLevel.HIGH.value: 3,
    ScaffoldLevel.MEDIUM.value: 2,
    ScaffoldLevel.LOW.value: 1,
    "three_step_visual": 3,
    "one_prompt": 2,
    "independent_try": 1,
}


def display_name(skill_code: str) -> str:
    catalog = definition_by_code()
    item = catalog.get(skill_code)
    if item is None:
        return skill_code
    return str(item["display_name"])


def next_win_implication(
    *,
    previous: InstructionPlan | None,
    upcoming: InstructionPlan,
    evidence_result: str | None,
) -> str:
    if previous is None:
        return "First instructional decision for this learner."
    if upcoming.scheduled_goal_code and previous.scheduled_goal_code:
        if upcoming.scheduled_goal_code != previous.scheduled_goal_code:
            return upcoming.scheduler_why_selected or (
                f"The next Win moves from {display_name(previous.primary_skill_code)} "
                f"to {display_name(upcoming.primary_skill_code)}."
            )
    if upcoming.primary_skill_code != previous.primary_skill_code:
        if "placement_step_down" in upcoming.selection_reason_codes:
            return (
                f"The diagnostic required significant help, so the next Win "
                f"steps down to {display_name(upcoming.primary_skill_code)}."
            )
        if "prerequisite_evidence_missing" in upcoming.selection_reason_codes:
            return (
                f"Prerequisite evidence was weak, so the next Win teaches "
                f"{display_name(upcoming.primary_skill_code)}."
            )
        if upcoming.instruction_mode.value == "review":
            return (
                f"A retained skill is due for review, so the next Win revisits "
                f"{display_name(upcoming.primary_skill_code)}."
            )
        return (
            f"The next Win moves from {display_name(previous.primary_skill_code)} "
            f"to {display_name(upcoming.primary_skill_code)}."
        )
    prev_rank = _SCAFFOLD_RANK.get(previous.scaffold_level.value, 0)
    next_rank = _SCAFFOLD_RANK.get(upcoming.scaffold_level.value, 0)
    if next_rank < prev_rank:
        return "Recent independent evidence reduced the required scaffold."
    if next_rank > prev_rank:
        return "Recent supported or incorrect evidence increased the required scaffold."
    if upcoming.instruction_mode != previous.instruction_mode:
        return (
            f"Mode changed from {previous.instruction_mode.value} to "
            f"{upcoming.instruction_mode.value}."
        )
    if evidence_result == "correct_independently":
        return "The same skill continues while more independent evidence is gathered."
    if evidence_result in {"incorrect", "correct_after_significant_help"}:
        return (
            "The same skill continues because independent evidence is not yet "
            "sufficient."
        )
    return "The next Win stays on the same skill with a similar plan."


def why_not_explanations(plan: InstructionPlan, data: PlannerInput) -> WhyNotTrace:
    primary = plan.primary_skill_code
    nxt = _next_in_strand(primary)
    prev = _previous_in_strand(primary)
    why_next = "No later skill is defined on this strand."
    if nxt is not None:
        nxt_name = display_name(nxt)
        state = data.states.get(primary)
        band = (
            state.academic.band
            if state and state.academic
            else AcademicBand.NOT_OBSERVED
        )
        if band not in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}:
            why_next = (
                f"Daily Win did not select {nxt_name} because "
                f"{display_name(primary)} does not yet have sufficient evidence."
            )
        else:
            why_next = (
                f"Daily Win did not select {nxt_name} because "
                f"{display_name(primary)} is the current instructional target."
            )
    why_prev = "No earlier skill is defined on this strand."
    if prev is not None:
        prev_state = data.states.get(prev)
        prev_band = (
            prev_state.academic.band
            if prev_state and prev_state.academic
            else AcademicBand.NOT_OBSERVED
        )
        if prev_band is AcademicBand.RETAINED:
            due = False
            if prev_state and prev_state.academic:
                due = due_for_review(prev_state.academic, now=data.now)
            if due:
                why_prev = (
                    f"{display_name(prev)} is retained and due for review, but "
                    f"an active instructional need was a higher priority."
                )
            else:
                why_prev = (
                    f"{display_name(prev)} is already retained and is not due "
                    f"for review."
                )
        elif prev_band in {AcademicBand.DEMONSTRATED, AcademicBand.DEVELOPING}:
            why_prev = (
                f"{display_name(prev)} already has usable evidence and is not "
                f"the current target."
            )
        else:
            why_prev = (
                f"{display_name(prev)} was not selected because placement started "
                f"at an age-appropriate entry skill."
            )
    academic_goals = [
        goal.skill_code
        for goal in sorted(data.goals, key=lambda item: item.priority)
        if is_academic_code(goal.skill_code)
    ]
    why_second = "Only one academic goal is currently selected."
    if len(academic_goals) >= 2:
        first = academic_goals[0]
        second = academic_goals[1]
        selected_goal = plan.scheduled_goal_code or first
        other = second if selected_goal == first else first
        deferred = " ".join(plan.scheduler_why_deferred)
        if selected_goal == second:
            why_second = plan.scheduler_why_selected or (
                f"Today targets {display_name(second)}; "
                f"{display_name(first)} remains active."
            )
        elif deferred:
            why_second = deferred
        else:
            why_second = (
                f"{display_name(other)} is active but {display_name(selected_goal)} "
                f"had a stronger scheduling claim today."
            )
    why_review = "Active learning was preferred over review."
    if plan.instruction_mode.value == "review":
        why_review = (
            "A review was scheduled because a retained skill is due and "
            "active-learning candidates were weaker or absent."
        )
    elif (
        plan.scheduler_reason_codes
        and "review_candidate" not in plan.scheduler_reason_codes
    ):
        why_review = (
            "A review was not selected because active learning or remediation "
            "had higher urgency, or recent Wins already included reviews."
        )
    why_terminal = "The current target is not a retained terminal skill."
    if "terminal_maintenance_transfer" in plan.selection_reason_codes:
        why_terminal = (
            "The retained terminal skill is in maintenance; ordinary repeated "
            "practice has stopped."
        )
    elif plan.deferred_goals:
        why_terminal = (
            "A retained terminal skill was not selected because another active "
            "goal still has instructional work."
        )
    protocol = plan.coach_protocol if isinstance(plan.coach_protocol, dict) else {}
    why_coaching = str(protocol.get("why_this_coaching") or "")
    why_wait = None
    if protocol.get("wait_guidance"):
        why_wait = str(
            protocol.get("why_this_coaching") or protocol.get("assessment_boundary")
        )
    why_model = None
    ceiling = str(protocol.get("prompt_ceiling") or "")
    if ceiling in {"analogous_model", "reduce_one_step"}:
        why_model = (
            "Today's mode allows a similar example after an independent attempt."
        )
    why_reduce = None
    if (
        plan.instruction_mode.value == "remediation"
        or plan.scaffold_level.value == "three_step_visual"
    ):
        why_reduce = (
            "Repeated support or a weak diagnostic means reduce one step, "
            "not push harder."
        )
    why_explain = None
    if plan.teach_the_coach:
        why_explain = (
            "Practice/review for an older child can ask them to explain the strategy."
        )
    return WhyNotTrace(
        why_not_next_skill=why_next,
        why_not_previous_skill=why_prev,
        why_not_second_goal=why_second,
        why_not_review=why_review,
        why_not_terminal=why_terminal,
        why_this_coaching=why_coaching or None,
        why_wait=why_wait,
        why_model_allowed=why_model,
        why_reduce=why_reduce,
        why_ask_for_explanation=why_explain,
    )


def preview_reason(plan: InstructionPlan) -> str:
    if plan.scheduler_why_selected:
        return plan.scheduler_why_selected
    if "placement_step_down" in plan.selection_reason_codes:
        return "weak grade-level diagnostic"
    if "grade_band_prior" in plan.selection_reason_codes:
        return "age/grade placement with sparse evidence"
    if plan.instruction_mode.value == "review":
        return "retained skill is due for review"
    if plan.instruction_mode.value == "remediation":
        return "recent evidence needs remediation"
    if "prerequisite_evidence_missing" in plan.selection_reason_codes:
        return "prerequisite evidence is still weak"
    if plan.instruction_mode.value == "diagnostic":
        return "diagnostic check at the current entry skill"
    return "parent priority and current learner state"


def _next_in_strand(skill_code: str) -> str | None:
    dependents = dependents_for(skill_code)
    return dependents[0] if dependents else None


def _previous_in_strand(skill_code: str) -> str | None:
    prereqs = prerequisites_for(skill_code)
    return prereqs[0] if prereqs else None
