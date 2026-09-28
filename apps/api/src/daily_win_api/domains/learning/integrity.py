"""Curriculum integrity invariants. Fail CI if the academic engine is incomplete."""

from datetime import UTC, datetime, timedelta

from daily_win_api.domains.learning.academic import (
    ACADEMIC_PROJECTOR_V1,
    AcademicStateSnapshot,
)
from daily_win_api.domains.learning.enums import AcademicBand, SkillKind
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    PlannerInput,
    PlannerSkillState,
    plan_instruction,
)
from daily_win_api.domains.learning.prerequisites import (
    PREREQUISITE_EDGES,
    assert_prerequisites_valid,
    prerequisites_for,
)
from daily_win_api.domains.learning.probes import (
    GENERIC_PROBE_TASK,
    has_construct_specific_probe,
    probe_for_skill,
)
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import (
    SKILL_DEFINITIONS,
    definition_by_code,
    is_academic_code,
    is_generation_supported,
)

_INTEGRITY_NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def academic_skill_codes() -> tuple[str, ...]:
    return tuple(
        str(item["code"])
        for item in SKILL_DEFINITIONS
        if item.get("skill_kind") == SkillKind.SKILL.value
        and is_academic_code(str(item["code"]))
    )


def curriculum_integrity_errors() -> list[str]:
    errors: list[str] = []
    catalog = definition_by_code()
    try:
        assert_prerequisites_valid()
    except ValueError as exc:
        errors.append(str(exc))

    codes = academic_skill_codes()
    active = tuple(code for code in codes if is_generation_supported(code))
    for code in active:
        if not has_construct_specific_probe(code):
            errors.append(f"missing_construct_probe:{code}")
            continue
        probe = probe_for_skill(code)
        if probe.get("target_skill_code") != code:
            errors.append(f"probe_target_mismatch:{code}")
        task = str(probe.get("observable_task") or "")
        if task == GENERIC_PROBE_TASK:
            errors.append(f"generic_probe:{code}")
        if not str(probe.get("expected_outcome") or "").strip():
            errors.append(f"probe_missing_outcome:{code}")
        if not str(probe.get("success_criteria") or "").strip():
            errors.append(f"probe_missing_success:{code}")

    mapped = {item["skill_code"] for item in SKILL_STANDARD_REFS}
    for code in active:
        if code not in mapped:
            errors.append(f"missing_standard_ref:{code}")
    for item in SKILL_STANDARD_REFS:
        skill = item["skill_code"]
        if skill not in catalog:
            errors.append(f"standard_unknown_skill:{skill}")
        elif not is_academic_code(skill):
            errors.append(f"standard_on_non_academic:{skill}")

    strand_positions: dict[str, list[int]] = {}
    for item in SKILL_DEFINITIONS:
        if item.get("skill_kind") != SkillKind.SKILL.value:
            continue
        parent = str(item.get("parent_code") or "")
        strand_positions.setdefault(parent, []).append(
            int(item["progression_position"])
        )
    for parent, positions in strand_positions.items():
        if len(positions) != len(set(positions)):
            errors.append(f"duplicate_progression_position:{parent}")

    for src, dest in PREREQUISITE_EDGES:
        if catalog[src].get("parent_code") == catalog[dest].get("parent_code"):
            src_pos = int(catalog[src]["progression_position"])
            dest_pos = int(catalog[dest]["progression_position"])
            if src_pos >= dest_pos:
                errors.append(f"within_strand_order:{src}->{dest}")

    errors.extend(_planner_reachability_errors())
    return errors


def assert_curriculum_integrity() -> None:
    errors = curriculum_integrity_errors()
    if errors:
        raise AssertionError("; ".join(errors))


def _retained_snapshot() -> AcademicStateSnapshot:
    practiced = _INTEGRITY_NOW - timedelta(days=1)
    return AcademicStateSnapshot(
        band=AcademicBand.RETAINED,
        algorithm_version=ACADEMIC_PROJECTOR_V1,
        usable_evidence_count=4,
        distinct_session_count=4,
        last_practiced_at=practiced,
        last_independent_success_at=practiced,
        evidence_ids=(),
        summary="integrity",
        needs_remediation=False,
    )


def _planner_reachability_errors() -> list[str]:
    errors: list[str] = []
    retained = _retained_snapshot()
    for code in academic_skill_codes():
        if not is_generation_supported(code):
            plan = _plan_for(code, {})
            if plan.primary_skill_code == code:
                errors.append(f"unsupported_selected:{code}")
            continue
        states = {
            prereq: PlannerSkillState(prereq, retained) for prereq in _all_prereqs(code)
        }
        plan = _plan_for(code, states)
        if plan.primary_skill_code != code:
            errors.append(f"unreachable:{code}->selected {plan.primary_skill_code}")
        if not has_construct_specific_probe(plan.primary_skill_code):
            errors.append(f"unmeasurable_selected:{plan.primary_skill_code}")
        supporting = plan.supporting_skill_code
        if (
            supporting
            and supporting.startswith(("math.", "reading.", "writing."))
            and not is_generation_supported(supporting)
        ):
            errors.append(f"unsupported_supporting:{supporting}")
    return errors


def _plan_for(code: str, states: dict[str, PlannerSkillState]):
    return plan_instruction(
        PlannerInput(
            nickname="Eval",
            age_years=8,
            grade="3",
            interests=("space",),
            motivators=("stories",),
            preferred_duration_minutes=20,
            goals=(GoalPriority(code, 1),),
            states=states,
            recent_skill_codes=(),
            recent_themes=(),
            now=_INTEGRITY_NOW,
        )
    )


def _all_prereqs(code: str, seen: set[str] | None = None) -> tuple[str, ...]:
    seen = seen if seen is not None else set()
    found: list[str] = []
    for prereq in prerequisites_for(code):
        if prereq in seen:
            continue
        seen.add(prereq)
        found.extend(_all_prereqs(prereq, seen))
        found.append(prereq)
    return tuple(found)
