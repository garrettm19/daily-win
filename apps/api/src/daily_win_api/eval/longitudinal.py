"""Offline longitudinal simulator using the real planner, placement, and projector.

Does not write learner_skill_state. Evidence is accumulated as AcademicEvidence
and rebuilt through project_academic_band.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from daily_win_api.domains.learning.academic import (
    AcademicEvidence,
    project_academic_band,
)
from daily_win_api.domains.learning.enums import AcademicBand, AcademicResult
from daily_win_api.domains.learning.placement import PLACEMENT_SKILLS, decide_placement
from daily_win_api.domains.learning.planner import (
    GoalPriority,
    InstructionPlan,
    PlannerInput,
    PlannerSkillState,
    plan_instruction,
    plan_instruction_v3,
)
from daily_win_api.domains.learning.signals import PERSISTENCE_SKILL_CODE
from daily_win_api.domains.learning.taxonomy import (
    is_academic_code,
    is_growth_or_life_code,
    strand_code_for,
)
from daily_win_api.eval.scoring import write_results

SIM_START = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
RESULTS_DIR = Path(__file__).resolve().parents[3] / "eval-results"

_INDEPENDENT = AcademicResult.CORRECT_INDEPENDENTLY
_PROMPT = AcademicResult.CORRECT_AFTER_LIGHT_PROMPT
_HELP = AcademicResult.CORRECT_AFTER_SIGNIFICANT_HELP
_INCORRECT = AcademicResult.INCORRECT


@dataclass(frozen=True)
class Archetype:
    id: str
    name: str
    nickname: str
    age_years: int
    grade: str
    goals: tuple[tuple[str, int], ...]
    interests: tuple[str, ...] = ("soccer",)
    duration: int = 20


@dataclass
class SimWin:
    index: int
    occurred_at: datetime
    plan: InstructionPlan
    academic_result: AcademicResult | None
    persistence: str
    before_band: str
    after_band: str


@dataclass
class Anomaly:
    severity: str
    code: str
    detail: str
    archetype: str


@dataclass
class SimHistory:
    archetype: Archetype
    weeks: int
    wins_per_week: int
    wins: list[SimWin] = field(default_factory=list)
    evidence: dict[str, list[AcademicEvidence]] = field(default_factory=dict)
    anomalies: list[Anomaly] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)


ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        "A",
        "fast_progressor",
        "Avery",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "B",
        "typical_progressor",
        "Blair",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "C",
        "foundational_gap",
        "Casey",
        9,
        "4",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "D",
        "inconsistent",
        "Drew",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "E",
        "low_persistence_strong_academics",
        "Eden",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "F",
        "strong_persistence_weak_academics",
        "Finn",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "G",
        "sparse_user",
        "Gray",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "H",
        "frequent_user",
        "Harper",
        8,
        "3",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "I",
        "new_older",
        "Indigo",
        9,
        "4",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "J",
        "new_younger",
        "Jules",
        5,
        "K",
        (("writing.spelling", 1), ("growth.persistence", 2)),
    ),
)

CONFLICT_ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        "K",
        "writing_vs_spelling_gap",
        "Kai",
        9,
        "4",
        (
            ("writing.organization", 1),
            ("writing.spelling", 2),
            ("growth.persistence", 3),
        ),
    ),
    Archetype(
        "L",
        "advanced_math_weak_prereq",
        "Lane",
        9,
        "4",
        (("math.addition", 1), ("growth.persistence", 2)),
    ),
    Archetype(
        "M",
        "multi_goal_spelling_math_persistence",
        "Morgan",
        8,
        "3",
        (
            ("writing.spelling", 1),
            ("math.addition", 2),
            ("growth.persistence", 3),
        ),
    ),
)


def simulate(
    archetype: Archetype,
    *,
    weeks: int,
    wins_per_week: int,
    interests: tuple[str, ...] | None = None,
    policy: str = "v4",
) -> SimHistory:
    history = SimHistory(archetype=archetype, weeks=weeks, wins_per_week=wins_per_week)
    interests = interests or archetype.interests
    evidence: dict[str, list[AcademicEvidence]] = {}
    growth_signals: list[str] = []
    recent_skills: list[str] = []
    recent_themes: list[str] = []
    recent_modes: list[str] = []
    recent_goals: list[str] = []
    day_gap = max(1, 7 // max(wins_per_week, 1))
    planner = plan_instruction_v3 if policy == "v3" else plan_instruction
    index = 0
    for week in range(weeks):
        for slot in range(wins_per_week):
            now = SIM_START + timedelta(days=week * 7 + slot * day_gap)
            states = _states_from_evidence(evidence, growth_signals, now)
            data = PlannerInput(
                nickname=archetype.nickname,
                age_years=archetype.age_years,
                grade=archetype.grade,
                interests=interests,
                motivators=("stories",),
                preferred_duration_minutes=archetype.duration,
                goals=tuple(
                    GoalPriority(code, priority) for code, priority in archetype.goals
                ),
                states=states,
                recent_skill_codes=tuple(recent_skills[:8]),
                recent_themes=tuple(recent_themes[:3]),
                now=now,
                recent_instruction_modes=tuple(recent_modes[:8]),
                recent_goal_codes=tuple(recent_goals[:8]),
            )
            plan = planner(data)
            before_band = _band(states, plan.primary_skill_code)
            result, persistence = _respond(archetype, plan, index, history.wins)
            if result is not None and is_academic_code(plan.primary_skill_code):
                evidence.setdefault(plan.primary_skill_code, []).append(
                    AcademicEvidence(
                        event_id=uuid4(),
                        occurred_at=now,
                        result=result,
                        session_key=f"win-{index}",
                    )
                )
            growth_signals.append(persistence)
            after = _states_from_evidence(evidence, growth_signals, now)
            history.wins.append(
                SimWin(
                    index=index,
                    occurred_at=now,
                    plan=plan,
                    academic_result=result,
                    persistence=persistence,
                    before_band=before_band,
                    after_band=_band(after, plan.primary_skill_code),
                )
            )
            recent_skills.insert(0, plan.primary_skill_code)
            recent_themes.insert(0, f"{interests[0]}-{plan.primary_skill_code}")
            recent_modes.insert(0, plan.instruction_mode.value)
            recent_goals.insert(
                0, plan.scheduled_goal_code or strand_code_for(plan.primary_skill_code)
            )
            index += 1
    history.evidence = evidence
    history.metrics = _metrics(history)
    history.anomalies = detect_anomalies(history)
    return history


def detect_anomalies(history: SimHistory) -> list[Anomaly]:
    wins = history.wins
    flags: list[Anomaly] = []
    aid = history.archetype.id
    if not wins:
        return flags
    skills = [item.plan.primary_skill_code for item in wins]
    consecutive = 1
    for index, (previous, current) in enumerate(
        zip(skills, skills[1:], strict=False), start=1
    ):
        consecutive = consecutive + 1 if previous == current else 1
        if consecutive < 8:
            continue
        item = wins[index]
        retained_practice = (
            item.plan.instruction_mode.value == "practice"
            and item.after_band
            in {AcademicBand.RETAINED.value, AcademicBand.DEMONSTRATED.value}
            and "terminal_maintenance_transfer" not in item.plan.selection_reason_codes
        )
        if retained_practice:
            flags.append(
                _flag(
                    "HIGH",
                    "SKILL_LOOP",
                    aid,
                    f"{current} selected {consecutive} times in a row after retained",
                )
            )
            break
    ping = 0
    for i in range(len(skills) - 3):
        if (
            skills[i] == skills[i + 2]
            and skills[i + 1] == skills[i + 3]
            and skills[i] != skills[i + 1]
        ):
            ping += 1
    if ping >= 4:
        flags.append(_flag("HIGH", "PING_PONG", aid, f"A/B alternation count {ping}"))
    foundation_hits = [
        item
        for item in wins
        if PLACEMENT_SKILLS.get(item.plan.primary_skill_code)
        and PLACEMENT_SKILLS[item.plan.primary_skill_code].foundation_for_older
        and history.archetype.age_years >= 8
    ]
    independent_on_foundation = [
        item for item in foundation_hits if item.academic_result is _INDEPENDENT
    ]
    if len(foundation_hits) >= 12 and len(independent_on_foundation) >= 4:
        flags.append(
            _flag(
                "HIGH",
                "PERMANENT_FOUNDATION_LOOP",
                aid,
                "Older learner stayed on foundational skill after independent evidence",
            )
        )
    under = 0
    streak = 0
    last_skill = None
    for item in wins:
        if (
            item.academic_result is _INDEPENDENT
            and item.plan.primary_skill_code == last_skill
        ):
            streak += 1
        else:
            streak = 1 if item.academic_result is _INDEPENDENT else 0
        last_skill = item.plan.primary_skill_code
        if streak >= 6 and item.plan.instruction_mode.value != "review":
            under += 1
    if under >= 1:
        flags.append(
            _flag(
                "MEDIUM",
                "UNDER_ADVANCEMENT",
                aid,
                "Repeated independent evidence did not move off the skill",
            )
        )
    rem_trap = 0
    rem_then_strong = 0
    for item in wins:
        if item.plan.instruction_mode.value == "remediation":
            rem_trap += 1
        if rem_trap and item.academic_result is _INDEPENDENT:
            rem_then_strong += 1
    if rem_trap >= 8 and rem_then_strong >= 3:
        flags.append(
            _flag(
                "HIGH",
                "REMEDIATION_TRAP",
                aid,
                "Remediation continued after later independent evidence",
            )
        )
    reviews = sum(1 for item in wins if item.plan.instruction_mode.value == "review")
    if wins and reviews / len(wins) >= 0.45:
        flags.append(
            _flag(
                "MEDIUM",
                "REVIEW_OVERLOAD",
                aid,
                f"{reviews}/{len(wins)} wins were reviews",
            )
        )
    retained_never_reviewed = False
    saw_retained_target = False
    for item in wins:
        if item.after_band == AcademicBand.RETAINED.value:
            saw_retained_target = True
        if item.plan.instruction_mode.value == "review":
            retained_never_reviewed = False
            break
    else:
        retained_never_reviewed = saw_retained_target and len(wins) >= 20
    if retained_never_reviewed:
        flags.append(
            _flag(
                "MEDIUM",
                "REVIEW_STARVATION",
                aid,
                "Retained skills were never revisited",
            )
        )
    academic_goals = [
        code for code, _priority in history.archetype.goals if is_academic_code(code)
    ]
    if len(academic_goals) >= 2 and len(wins) >= 20:
        second = academic_goals[1]
        primary_domain = academic_goals[0].split(".")[0]
        second_domain = second.split(".")[0]
        if second_domain == primary_domain:
            second_hits = sum(1 for code in skills if code.startswith(second))
        else:
            second_hits = sum(
                1 for code in skills if code.split(".")[0] == second_domain
            )
        if second_hits == 0:
            flags.append(
                _flag(
                    "HIGH",
                    "GOAL_STARVATION",
                    aid,
                    f"Priority #2 {second} received no primary instructional time",
                )
            )
        else:
            gap = 0
            max_gap = 0
            for code in skills:
                hit = (
                    code.startswith(second)
                    if second_domain == primary_domain
                    else code.split(".")[0] == second_domain
                )
                if hit:
                    max_gap = max(max_gap, gap)
                    gap = 0
                else:
                    gap += 1
            max_gap = max(max_gap, gap)
            if max_gap > 6:
                flags.append(
                    _flag(
                        "HIGH",
                        "GOAL_STARVATION",
                        aid,
                        f"Priority #2 {second} neglected for {max_gap} Wins",
                    )
                )
    growth_as_primary = sum(1 for code in skills if is_growth_or_life_code(code))
    if growth_as_primary >= 3:
        flags.append(
            _flag(
                "MEDIUM",
                "GROWTH_DOMINANCE",
                aid,
                "Growth target selected as primary skill",
            )
        )
    kindergarten_dump = [
        item
        for item in wins[:4]
        if history.archetype.age_years >= 9
        and item.plan.primary_skill_code
        in {
            "writing.spelling.cvc",
            "reading.phonics.letter_sounds",
            "math.number_sense.counting",
        }
        and item.index == 0
    ]
    if kindergarten_dump:
        flags.append(
            _flag(
                "CRITICAL",
                "KINDERGARTEN_DUMP",
                aid,
                "Age-9 first Win dumped to a kindergarten/foundation skill",
            )
        )
    return flags


def scheduler_before_after() -> dict[str, object]:
    morgan = next(item for item in CONFLICT_ARCHETYPES if item.id == "M")
    gray = next(item for item in ARCHETYPES if item.id == "G")
    indigo = next(item for item in ARCHETYPES if item.id == "I")
    old_m = simulate(morgan, weeks=7, wins_per_week=3, policy="v3")
    new_m = simulate(morgan, weeks=7, wins_per_week=3, policy="v4")
    old_g = simulate(gray, weeks=24, wins_per_week=1, policy="v3")
    new_g = simulate(gray, weeks=24, wins_per_week=1, policy="v4")
    old_i = simulate(indigo, weeks=12, wins_per_week=3, policy="v3")
    new_i = simulate(indigo, weeks=12, wins_per_week=3, policy="v4")
    return {
        "multi_goal_20": {
            "old_spelling": _count_skill(old_m, "spelling"),
            "old_math": _count_skill(old_m, "math."),
            "new_spelling": _count_skill(new_m, "spelling"),
            "new_math": _count_skill(new_m, "math."),
            "old_starvation": any(a.code == "GOAL_STARVATION" for a in old_m.anomalies),
            "new_starvation": any(a.code == "GOAL_STARVATION" for a in new_m.anomalies),
            "wins": len(new_m.wins),
        },
        "sparse_reviews": {
            "old": old_g.metrics.get("review_count"),
            "new": new_g.metrics.get("review_count"),
            "old_total": len(old_g.wins),
            "new_total": len(new_g.wins),
            "old_ping_pong": any(a.code == "PING_PONG" for a in old_g.anomalies),
            "new_ping_pong": any(a.code == "PING_PONG" for a in new_g.anomalies),
        },
        "terminal_spelling": {
            "old_unique": old_i.metrics.get("skills_targeted"),
            "new_unique": new_i.metrics.get("skills_targeted"),
            "old_loop": any(a.code == "SKILL_LOOP" for a in old_i.anomalies),
            "new_loop": any(a.code == "SKILL_LOOP" for a in new_i.anomalies),
            "old_under": any(a.code == "UNDER_ADVANCEMENT" for a in old_i.anomalies),
            "new_under": any(a.code == "UNDER_ADVANCEMENT" for a in new_i.anomalies),
            "old_last_skills": [
                item.plan.primary_skill_code for item in old_i.wins[-8:]
            ],
            "new_last_skills": [
                item.plan.primary_skill_code for item in new_i.wins[-8:]
            ],
            "old_last_modes": [
                item.plan.instruction_mode.value for item in old_i.wins[-8:]
            ],
            "new_last_modes": [
                item.plan.instruction_mode.value for item in new_i.wins[-8:]
            ],
        },
        "cadence_matrix": _scheduler_cadence_matrix(),
    }


def _scheduler_cadence_matrix() -> list[dict[str, object]]:
    morgan = next(item for item in CONFLICT_ARCHETYPES if item.id == "M")
    gray = next(item for item in ARCHETYPES if item.id == "G")
    indigo = next(item for item in ARCHETYPES if item.id == "I")
    rows: list[dict[str, object]] = []
    plans = (
        (morgan, 4, 1),
        (morgan, 4, 3),
        (morgan, 4, 5),
        (morgan, 12, 1),
        (morgan, 12, 3),
        (morgan, 12, 5),
        (morgan, 24, 1),
        (morgan, 24, 3),
        (morgan, 24, 5),
        (gray, 4, 1),
        (gray, 12, 1),
        (gray, 24, 1),
        (indigo, 4, 3),
        (indigo, 12, 3),
        (indigo, 24, 3),
    )
    for archetype, weeks, cadence in plans:
        history = simulate(archetype, weeks=weeks, wins_per_week=cadence)
        modes = [item.plan.instruction_mode.value for item in history.wins]
        rows.append(
            {
                "archetype": archetype.id,
                "weeks": weeks,
                "wins_per_week": cadence,
                "wins": len(history.wins),
                "spelling": _count_skill(history, "spelling"),
                "math": _count_skill(history, "math."),
                "review": modes.count("review"),
                "diagnostic": modes.count("diagnostic"),
                "practice": modes.count("practice") + modes.count("introduce"),
                "remediation": modes.count("remediation"),
                "terminal_maintenance": sum(
                    1
                    for item in history.wins
                    if "terminal_maintenance_transfer"
                    in item.plan.selection_reason_codes
                ),
                "starvation": any(
                    a.code == "GOAL_STARVATION" for a in history.anomalies
                ),
                "ping_pong": any(a.code == "PING_PONG" for a in history.anomalies),
                "skill_loop": any(a.code == "SKILL_LOOP" for a in history.anomalies),
                "max_consecutive": _max_consecutive_goal(history),
                "max_neglect": _max_goal_neglect(history),
            }
        )
    return rows


def _max_consecutive_goal(history: SimHistory) -> int:
    goals = [
        item.plan.scheduled_goal_code or strand_code_for(item.plan.primary_skill_code)
        for item in history.wins
    ]
    best = current = 0
    previous = None
    for code in goals:
        current = current + 1 if code == previous else 1
        best = max(best, current)
        previous = code
    return best


def _max_goal_neglect(history: SimHistory) -> int:
    academic = [
        code for code, _priority in history.archetype.goals if is_academic_code(code)
    ]
    if len(academic) < 2 or not history.wins:
        return 0
    second = academic[1]
    gap = 0
    best = 0
    for item in history.wins:
        goal = item.plan.scheduled_goal_code or strand_code_for(
            item.plan.primary_skill_code
        )
        hit = goal == second or item.plan.primary_skill_code.startswith(second)
        if hit:
            best = max(best, gap)
            gap = 0
        else:
            gap += 1
    return max(best, gap)


def _count_skill(history: SimHistory, token: str) -> int:
    return sum(
        1
        for item in history.wins
        if token in item.plan.primary_skill_code
        or item.plan.primary_skill_code.startswith(token)
    )


def run_longitudinal_suite(*, write_report: bool = True) -> dict[str, object]:
    histories: list[SimHistory] = []
    plans = (
        ("A", 12, 3),
        ("B", 12, 3),
        ("C", 12, 3),
        ("D", 12, 3),
        ("E", 8, 3),
        ("F", 8, 3),
        ("G", 24, 1),
        ("H", 12, 5),
        ("I", 4, 3),
        ("J", 4, 3),
        ("A", 24, 5),
        ("C", 24, 3),
        ("B", 4, 1),
    )
    by_id = {item.id: item for item in ARCHETYPES}
    for aid, weeks, cadence in plans:
        histories.append(simulate(by_id[aid], weeks=weeks, wins_per_week=cadence))
    for extra in CONFLICT_ARCHETYPES:
        histories.append(simulate(extra, weeks=8, wins_per_week=3))
    histories.append(
        simulate(by_id["A"], weeks=4, wins_per_week=3, interests=("Minecraft",))
    )
    interest_base = simulate(
        by_id["A"], weeks=4, wins_per_week=3, interests=("soccer",)
    )
    interest_alt = simulate(by_id["A"], weeks=4, wins_per_week=3, interests=("space",))
    interest_invariant = all(
        left.plan.primary_skill_code == right.plan.primary_skill_code
        and left.plan.scaffold_level == right.plan.scaffold_level
        and left.plan.intended_difficulty == right.plan.intended_difficulty
        and left.plan.instruction_mode == right.plan.instruction_mode
        for left, right in zip(
            interest_base.wins, interest_alt.wins, strict=False
        )
    )
    recency = recency_audit()
    contradiction = contradiction_audit()
    step_down = step_down_audit()
    step_up = step_up_audit()
    goal_alloc = goal_allocation_audit()
    comparison = scheduler_before_after()
    anomalies = [item for history in histories for item in history.anomalies]
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "suite": "longitudinal",
        "note": "Offline simulation. Not learner memory. No live OpenAI.",
        "interest_invariant": interest_invariant,
        "histories": [_history_summary(item) for item in histories],
        "anomalies": [
            {
                "severity": item.severity,
                "code": item.code,
                "archetype": item.archetype,
                "detail": item.detail,
            }
            for item in anomalies
        ],
        "recency": recency,
        "contradiction": contradiction,
        "step_down": step_down,
        "step_up": step_up,
        "goal_allocation": goal_alloc,
        "scheduler_before_after": comparison,
        "query_index_notes": query_index_notes(),
        "policy_notes": policy_notes(),
    }
    if write_report:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        write_results(RESULTS_DIR / f"{stamp}-longitudinal-engine-audit.json", payload)
        (RESULTS_DIR / "longitudinal-engine-audit.md").write_text(
            render_markdown(payload),
            encoding="utf-8",
        )
        (RESULTS_DIR / f"{stamp}-scheduler-audit.md").write_text(
            render_scheduler_audit(payload),
            encoding="utf-8",
        )
        (RESULTS_DIR / "scheduler-audit.md").write_text(
            render_scheduler_audit(payload),
            encoding="utf-8",
        )
    return payload


def recency_audit() -> dict[str, object]:
    now = SIM_START + timedelta(days=100)
    strong_recent = [
        AcademicEvidence(None, now - timedelta(days=2), _INDEPENDENT, "s1"),
    ]
    strong_old = [
        AcademicEvidence(None, now - timedelta(days=90), _INDEPENDENT, "s1"),
        AcademicEvidence(None, now - timedelta(days=83), _INDEPENDENT, "s2"),
    ]
    mixed = [
        AcademicEvidence(None, now - timedelta(days=90), _INDEPENDENT, "s1"),
        AcademicEvidence(None, now - timedelta(days=83), _INDEPENDENT, "s2"),
        AcademicEvidence(None, now - timedelta(days=1), _INCORRECT, "s3"),
    ]
    repeated_weak = [
        AcademicEvidence(None, now - timedelta(days=20), _INDEPENDENT, "s1"),
        AcademicEvidence(None, now - timedelta(days=13), _INDEPENDENT, "s2"),
        AcademicEvidence(None, now - timedelta(days=3), _HELP, "s3"),
        AcademicEvidence(None, now - timedelta(days=1), _INCORRECT, "s4"),
    ]
    return {
        "decay_mathematics": (
            "none — academic_projector_v1 has no time-decay of old independent "
            "evidence"
        ),
        "strong_2_days": project_academic_band(strong_recent, now=now).band.value,
        "strong_90_days_two_spaced": project_academic_band(
            strong_old, now=now
        ).band.value,
        "old_strong_plus_one_incorrect": {
            "band": project_academic_band(mixed, now=now).band.value,
            "needs_remediation": project_academic_band(
                mixed, now=now
            ).needs_remediation,
            "note": (
                "One incorrect after retained evidence does not flip "
                "recent_weak (needs last two sessions weak)."
            ),
        },
        "repeated_recent_weak_after_retained": {
            "band": project_academic_band(repeated_weak, now=now).band.value,
            "needs_remediation": project_academic_band(
                repeated_weak, now=now
            ).needs_remediation,
        },
    }


def contradiction_audit() -> dict[str, object]:
    now = SIM_START + timedelta(days=40)
    sequences = {
        "independent_independent_incorrect": [
            AcademicEvidence(None, now - timedelta(days=14), _INDEPENDENT, "a"),
            AcademicEvidence(None, now - timedelta(days=7), _INDEPENDENT, "b"),
            AcademicEvidence(None, now - timedelta(days=1), _INCORRECT, "c"),
        ],
        "incorrect_help_independent": [
            AcademicEvidence(None, now - timedelta(days=14), _INCORRECT, "a"),
            AcademicEvidence(None, now - timedelta(days=7), _HELP, "b"),
            AcademicEvidence(None, now - timedelta(days=1), _INDEPENDENT, "c"),
        ],
        "retained_then_incorrect_help": [
            AcademicEvidence(None, now - timedelta(days=21), _INDEPENDENT, "a"),
            AcademicEvidence(None, now - timedelta(days=14), _INDEPENDENT, "b"),
            AcademicEvidence(None, now - timedelta(days=3), _INCORRECT, "c"),
            AcademicEvidence(None, now - timedelta(days=1), _HELP, "d"),
        ],
        "weak_weak_independent_independent": [
            AcademicEvidence(None, now - timedelta(days=21), _HELP, "a"),
            AcademicEvidence(None, now - timedelta(days=14), _INCORRECT, "b"),
            AcademicEvidence(None, now - timedelta(days=8), _INDEPENDENT, "c"),
            AcademicEvidence(None, now - timedelta(days=1), _INDEPENDENT, "d"),
        ],
    }
    return {
        name: {
            "band": project_academic_band(items, now=now).band.value,
            "needs_remediation": project_academic_band(
                items, now=now
            ).needs_remediation,
            "sessions": project_academic_band(items, now=now).distinct_session_count,
        }
        for name, items in sequences.items()
    }


def step_down_audit() -> dict[str, object]:
    casey = next(item for item in ARCHETYPES if item.id == "C")
    history = simulate(casey, weeks=6, wins_per_week=3)
    path = [item.plan.primary_skill_code for item in history.wins]
    first = path[0] if path else None
    dumped = first in {
        "writing.spelling.cvc",
        "reading.phonics.letter_sounds",
        "math.number_sense.counting",
    }
    return {
        "first_skill": first,
        "unique_path": _unique_keep_order(path),
        "dumped_to_kindergarten": dumped,
        "reached_cvc": "writing.spelling.cvc" in path,
        "stayed_on_cvc_after_independent": any(
            item.plan.primary_skill_code == "writing.spelling.cvc"
            and item.academic_result is _INDEPENDENT
            for item in history.wins
        ),
    }


def step_up_audit() -> dict[str, object]:
    indigo = next(item for item in ARCHETYPES if item.id == "I")
    history = simulate(indigo, weeks=4, wins_per_week=3)
    path = [item.plan.primary_skill_code for item in history.wins]
    return {
        "first_skill": path[0] if path else None,
        "unique_path": _unique_keep_order(path),
        "first_mode": history.wins[0].plan.instruction_mode.value
        if history.wins
        else None,
        "repeated_diagnostic_count": sum(
            1
            for item in history.wins
            if item.plan.instruction_mode.value == "diagnostic"
        ),
        "note": (
            "One independent probe yields developing, not retained. "
            "Planner may continue the same skill to gather a second evidence point."
        ),
    }


def goal_allocation_audit() -> dict[str, object]:
    morgan = next(item for item in CONFLICT_ARCHETYPES if item.id == "M")
    history = simulate(morgan, weeks=7, wins_per_week=3)
    total = max(len(history.wins), 1)
    spelling = sum(
        1 for item in history.wins if "spelling" in item.plan.primary_skill_code
    )
    math = sum(
        1 for item in history.wins if item.plan.primary_skill_code.startswith("math.")
    )
    other = total - spelling - math
    overlay = sum(
        1
        for item in history.wins
        if item.plan.growth_target_code == PERSISTENCE_SKILL_CODE
    )
    return {
        "wins": total,
        "spelling": spelling,
        "spelling_pct": round(100 * spelling / total),
        "math": math,
        "math_pct": round(100 * math / total),
        "other": other,
        "persistence_overlay": overlay,
        "policy": (
            "instruction_scheduler_v1 prefers academic priority #1 but rotates "
            "after CONSECUTIVE_FOCUS_LIMIT=3 when another goal is eligible. "
            "Growth overlays do not consume academic slots."
        ),
    }


def query_index_notes() -> list[str]:
    return [
        "daily_wins: household/child/created index supports latest Win.",
        "instruction_plans: household/child/created index supports planner history.",
        "learning_events: household/child indexes; rebuild filters event_type.",
        "ContextBuilder caps events at 10 and wins at 3.",
        "Observatory as-of reconstruction is per-child, not a full table scan.",
        "No cache added. Observatory batches Skill lookups with IN().",
        "1000-child metadata load was not executed.",
    ]


def policy_notes() -> list[str]:
    return [
        "academic_projector_v1: two independent sessions → demonstrated.",
        "Spaced 7d independent sessions → retained.",
        "Regression needs the last two sessions weak after independent success.",
        "Review is due 14 days after last practice for demonstrated/retained.",
        "Goal weighting uses instruction_scheduler_v1 (priority preference, "
        "not monopoly).",
        "Review is due after 14 days but is a candidate, not an automatic selection.",
        "Mastery thresholds and spacing intervals were not changed.",
        "Parent-reported strengths do not overwrite measured state.",
    ]


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Longitudinal learning-engine audit",
        "",
        "Offline simulation using real placement_policy_v1, instruction_policy_v4,",
        "instruction_scheduler_v1, curriculum_v2, and academic_projector_v1. "
        "Not learner memory. No live OpenAI.",
        "",
        f"Interest invariant (soccer vs space): **{payload['interest_invariant']}**",
        "",
        "## Anomalies",
        "",
    ]
    anomalies = payload.get("anomalies") or []
    if not anomalies:
        lines.append("None flagged at configured thresholds.")
    for item in anomalies:
        lines.append(
            f"- **{item['severity']} / {item['code']}** "
            f"({item['archetype']}): {item['detail']}"
        )
    lines.extend(["", "## Histories", ""])
    for history in payload["histories"]:
        lines.append(
            f"### {history['archetype_id']} {history['name']} — "
            f"{history['weeks']}w × {history['wins_per_week']}/week"
        )
        lines.append(
            f"- wins: {history['wins']}; skills: {history['skills_targeted']}; "
            f"modes: {history['modes']}"
        )
        lines.append(f"- scaffold trajectory: {history['scaffold_trajectory']}")
        lines.append(f"- final skills: {history['final_bands']}")
        lines.append("")
    lines.extend(["", "## Recency", "", str(payload["recency"]), ""])
    lines.extend(["## Contradiction", "", str(payload["contradiction"]), ""])
    lines.extend(
        [
            "## Step-down / step-up",
            "",
            str(payload["step_down"]),
            "",
            str(payload["step_up"]),
            "",
        ]
    )
    lines.extend(["## Goal allocation", "", str(payload["goal_allocation"]), ""])
    lines.extend(
        [
            "## Scheduler before / after",
            "",
            str(payload.get("scheduler_before_after")),
            "",
        ]
    )
    lines.extend(["## Policy notes", ""])
    for note in payload["policy_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def render_scheduler_audit(payload: dict[str, object]) -> str:
    compare = payload.get("scheduler_before_after") or {}
    multi = compare.get("multi_goal_20") or {}
    sparse = compare.get("sparse_reviews") or {}
    terminal = compare.get("terminal_spelling") or {}
    lines = [
        "# Scheduler audit — V0.3.7 vs V0.3.8",
        "",
        "V0.3.7 = instruction_policy_v3 without scheduler.",
        "V0.3.8 = instruction_scheduler_v1 + instruction_policy_v4.",
        "REVIEW_AFTER_DAYS remains 14. Mastery thresholds unchanged.",
        "",
        "## 20-Win multi-goal (spelling #1, math #2, persistence overlay)",
        "",
        f"- OLD: spelling {multi.get('old_spelling')} / "
        f"math {multi.get('old_math')}",
        f"- NEW: spelling {multi.get('new_spelling')} / "
        f"math {multi.get('new_math')}",
        f"- OLD GOAL_STARVATION: {multi.get('old_starvation')}",
        f"- NEW GOAL_STARVATION: {multi.get('new_starvation')}",
        "",
        "## Sparse user reviews (24 weeks × 1 Win/week)",
        "",
        f"- OLD: {sparse.get('old')} / {sparse.get('old_total')} reviews; "
        f"ping-pong {sparse.get('old_ping_pong')}",
        f"- NEW: {sparse.get('new')} / {sparse.get('new_total')} reviews; "
        f"ping-pong {sparse.get('new_ping_pong')}",
        "",
        "## Terminal spelling (age 9, 12 weeks × 3/week)",
        "",
        f"- OLD unique skills: {terminal.get('old_unique')}; "
        f"loop {terminal.get('old_loop')}; "
        f"under-advancement {terminal.get('old_under')}",
        f"- NEW unique skills: {terminal.get('new_unique')}; "
        f"loop {terminal.get('new_loop')}; "
        f"under-advancement {terminal.get('new_under')}",
        "",
        "## Goal allocation (current policy)",
        "",
        str(payload.get("goal_allocation")),
        "",
        "## Cadence matrix (current scheduler)",
        "",
        "| arch | weeks | /wk | spell | math | review "
        "| starve | ping | loop | consec | neglect |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    matrix = compare.get("cadence_matrix") or []
    if isinstance(matrix, list):
        for row in matrix:
            if not isinstance(row, dict):
                continue
            lines.append(
                "| {archetype} | {weeks} | {wins_per_week} | {spelling} | "
                "{math} | {review} | {starvation} | {ping_pong} | "
                "{skill_loop} | {max_consecutive} | {max_neglect} |".format(
                    archetype=row.get("archetype"),
                    weeks=row.get("weeks"),
                    wins_per_week=row.get("wins_per_week"),
                    spelling=row.get("spelling"),
                    math=row.get("math"),
                    review=row.get("review"),
                    starvation=row.get("starvation"),
                    ping_pong=row.get("ping_pong"),
                    skill_loop=row.get("skill_loop"),
                    max_consecutive=row.get("max_consecutive"),
                    max_neglect=row.get("max_neglect"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _respond(
    archetype: Archetype,
    plan: InstructionPlan,
    index: int,
    prior: list[SimWin],
) -> tuple[AcademicResult | None, str]:
    skill_priors = [
        item
        for item in prior
        if item.plan.primary_skill_code == plan.primary_skill_code
    ]
    aid = archetype.id
    persistence = "continued_after_prompt"
    if aid == "E":
        persistence = "stopped_or_avoided"
    elif aid == "F":
        persistence = "kept_going_independently"
    elif aid == "A":
        persistence = "kept_going_independently"
    if not is_academic_code(plan.primary_skill_code):
        return None, persistence
    if aid == "A":
        return (_PROMPT if index % 7 == 0 else _INDEPENDENT), persistence
    if aid == "B":
        return (_PROMPT if len(skill_priors) < 2 else _INDEPENDENT), persistence
    if aid == "C":
        if (
            plan.instruction_mode.value == "diagnostic"
            or plan.primary_skill_code.endswith(
                ("endings_suffixes", "multisyllabic_irregular", "patterns")
            )
        ):
            if plan.primary_skill_code.endswith("cvc"):
                return _INDEPENDENT, persistence
            return _HELP, persistence
        return _INDEPENDENT, persistence
    if aid == "D":
        cycle = [_INDEPENDENT, _INDEPENDENT, _INCORRECT]
        return cycle[index % 3], persistence
    if aid == "E":
        return _INDEPENDENT, persistence
    if aid == "F":
        return _INCORRECT, persistence
    if aid in {"G", "H", "M"}:
        return (_PROMPT if len(skill_priors) < 2 else _INDEPENDENT), persistence
    if aid == "I":
        return _INDEPENDENT, persistence
    if aid == "J":
        return (_PROMPT if len(skill_priors) < 2 else _INDEPENDENT), persistence
    if aid == "K":
        if (
            "spelling" in plan.primary_skill_code
            and not plan.primary_skill_code.endswith("cvc")
        ):
            return _HELP, persistence
        return _PROMPT, persistence
    if aid == "L":
        if plan.primary_skill_code.endswith(("word_problems", "within_20")):
            return _HELP, persistence
        return _PROMPT, persistence
    return _PROMPT, persistence


def _states_from_evidence(
    evidence: dict[str, list[AcademicEvidence]],
    growth_signals: list[str],
    now: datetime,
) -> dict[str, PlannerSkillState]:
    states: dict[str, PlannerSkillState] = {}
    for code, items in evidence.items():
        snapshot = project_academic_band(items, now=now)
        states[code] = PlannerSkillState(skill_code=code, academic=snapshot)
    if growth_signals:
        states[PERSISTENCE_SKILL_CODE] = PlannerSkillState(
            skill_code=PERSISTENCE_SKILL_CODE,
            academic=None,
            latest_growth_signal=growth_signals[-1],
        )
    return states


def _band(states: dict[str, PlannerSkillState], code: str) -> str:
    state = states.get(code)
    if state is None or state.academic is None:
        return AcademicBand.NOT_OBSERVED.value
    return state.academic.band.value


def _metrics(history: SimHistory) -> dict[str, object]:
    skills = [item.plan.primary_skill_code for item in history.wins]
    modes = [item.plan.instruction_mode.value for item in history.wins]
    unique = sorted(set(skills))
    repeats = {code: skills.count(code) for code in unique}
    return {
        "wins": len(history.wins),
        "skills_targeted": unique,
        "repeats_per_skill": repeats,
        "diagnostic_count": modes.count("diagnostic"),
        "practice_count": modes.count("practice") + modes.count("introduce"),
        "remediation_count": modes.count("remediation"),
        "review_count": modes.count("review"),
        "scaffold_changes": sum(
            1
            for left, right in zip(history.wins, history.wins[1:], strict=False)
            if left.plan.scaffold_level != right.plan.scaffold_level
        ),
        "evidence_volume": sum(len(items) for items in history.evidence.values()),
    }


def _history_summary(history: SimHistory) -> dict[str, object]:
    modes: dict[str, int] = {}
    for item in history.wins:
        modes[item.plan.instruction_mode.value] = (
            modes.get(item.plan.instruction_mode.value, 0) + 1
        )
    scaffolds = [item.plan.scaffold_level.value for item in history.wins]
    final: dict[str, str] = {}
    for code, items in history.evidence.items():
        if items:
            final[code] = project_academic_band(
                items, now=items[-1].occurred_at
            ).band.value
    return {
        "archetype_id": history.archetype.id,
        "name": history.archetype.name,
        "weeks": history.weeks,
        "wins_per_week": history.wins_per_week,
        "wins": len(history.wins),
        "skills_targeted": history.metrics.get("skills_targeted"),
        "modes": modes,
        "scaffold_trajectory": _unique_keep_order(scaffolds),
        "final_bands": final,
        "anomalies": [item.code for item in history.anomalies],
        **{
            key: value
            for key, value in history.metrics.items()
            if key != "skills_targeted"
        },
    }


def _unique_keep_order(values: list[str]) -> list[str]:
    seen: list[str] = []
    for item in values:
        if not seen or seen[-1] != item:
            seen.append(item)
    return seen


def _flag(severity: str, code: str, archetype: str, detail: str) -> Anomaly:
    return Anomaly(severity=severity, code=code, detail=detail, archetype=archetype)


def cold_start_plan(age_years: int, goal: str) -> InstructionPlan:
    data = PlannerInput(
        nickname="Scout",
        age_years=age_years,
        grade="4" if age_years >= 9 else "K",
        interests=("soccer",),
        motivators=("stories",),
        preferred_duration_minutes=20,
        goals=(GoalPriority(goal, 1), GoalPriority(PERSISTENCE_SKILL_CODE, 2)),
        states={},
        recent_skill_codes=(),
        recent_themes=(),
        now=SIM_START,
    )
    return plan_instruction(data)


def placement_for(age_years: int, goal: str):
    return decide_placement(goal, age_years, {})
