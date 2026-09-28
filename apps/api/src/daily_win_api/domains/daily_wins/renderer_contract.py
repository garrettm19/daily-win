"""Deterministic renderer-contract checks. Conservative structure only."""

from __future__ import annotations

import re
from typing import Any

from daily_win_api.ai.schemas import DailyWinDraft, InstructionPlanContext
from daily_win_api.domains.daily_wins.schemas import RendererContractError
from daily_win_api.domains.learning.taxonomy import is_academic_code

THREE_CONCRETE_CUES = "three_concrete_cues"
DIAGNOSTIC_PROBE_BEFORE_TEACHING = "diagnostic_probe_before_teaching"
ONE_CANONICAL_ASSESSMENT = "one_canonical_assessment"
PRIMARY_SKILL_TIME_MAJORITY = "primary_skill_time_majority"
REVIEW_PRACTICE_THEN_CHECK = "review_practice_then_check"
FRESH_ASSESSMENT_ITEM = "fresh_assessment_item"
AGE_RESPECTFUL_FOUNDATION = "age_respectful_foundation"

SECTION_DURATION_IMPLAUSIBLE = "section_duration_implausible"
GROWTH_OVERLAY_DISCONNECTED = "growth_overlay_disconnected"
ASSESSMENT_LANGUAGE_AMBIGUOUS = "assessment_language_ambiguous"

HARD_RULE_CODES = frozenset(
    {
        THREE_CONCRETE_CUES,
        DIAGNOSTIC_PROBE_BEFORE_TEACHING,
        ONE_CANONICAL_ASSESSMENT,
        PRIMARY_SKILL_TIME_MAJORITY,
        REVIEW_PRACTICE_THEN_CHECK,
        FRESH_ASSESSMENT_ITEM,
        AGE_RESPECTFUL_FOUNDATION,
    }
)

_ACTION_START = re.compile(
    r"^(touch|say|move|point|ask|show|tap|trace|count|write|read|"
    r"blend|clap|hold|look|listen|draw|place|put|try|invite|wait|"
    r"pause|name|act|knock|rebuild|celebrate|cover|uncover|sort|"
    r"match|circle|underline|build)\b",
    re.IGNORECASE,
)
_TEACH = re.compile(
    r"\b(show|model|teach|explain how|demonstrate|walk them through|"
    r"practice together|let'?s practice)\b",
    re.IGNORECASE,
)
_CHECK = re.compile(
    r"\b(independent|on their own|without help|ask (one|the child)|"
    r"one (fact|word|item|check|try|sentence|problem)|probe|"
    r"what to check)\b",
    re.IGNORECASE,
)
_FINALISH = re.compile(
    r"\bfinal (challenge|mission|check|test)\b|\btest this one too\b",
    re.IGNORECASE,
)
_PRACTICE_LABEL = re.compile(r"\bpractice\b", re.IGNORECASE)
_PLAY_TOKENS = frozenset(
    {
        "soccer",
        "ball",
        "race",
        "tag",
        "kick",
        "dribble",
        "goalie",
        "stadium",
    }
)
_ITEMIZED_PREFIXES = (
    "math.addition",
    "math.subtraction",
    "math.number_sense.counting",
    "reading.phonics.blend_cvc",
    "writing.spelling",
)
_EQUATION = re.compile(r"\b\d+\s*[+\-−]\s*\d+\b")
_QUOTED = re.compile(r"[\"']([^\"']{2,24})[\"']")
_CVC_WORD = re.compile(
    r"\b(?:word|read|blend)\s+([a-z]{3})\b",
    re.IGNORECASE,
)
_THREE_STEP_PROSE = re.compile(
    r"\bthree[-\s]step\b|\bvisual process\b",
    re.IGNORECASE,
)
_BABY_TALK = re.compile(
    r"\b(baby words?|tiny words?|little kids?|little readers?|"
    r"kindergarten(?: style)?|baby animals?|for toddlers?|"
    r"sound it out like a baby|super easy baby|babyish|for babies|"
    r"good job, little)\b",
    re.IGNORECASE,
)


def contracts_for_plan(plan: Any) -> tuple[str, ...]:
    """Derived renderer contracts. Not stored learner truth."""
    rules = [ONE_CANONICAL_ASSESSMENT, PRIMARY_SKILL_TIME_MAJORITY]
    if _field(plan, "scaffold_level") == "three_step_visual":
        rules.append(THREE_CONCRETE_CUES)
    mode = _field(plan, "instruction_mode")
    if mode == "diagnostic":
        rules.append(DIAGNOSTIC_PROBE_BEFORE_TEACHING)
    if mode == "review":
        rules.append(REVIEW_PRACTICE_THEN_CHECK)
    if _itemized(_field(plan, "primary_skill_code")):
        rules.append(FRESH_ASSESSMENT_ITEM)
    if _field(plan, "presentation_constraint") == AGE_RESPECTFUL_FOUNDATION:
        rules.append(AGE_RESPECTFUL_FOUNDATION)
    return tuple(rules)


def validate_renderer_contract(draft: DailyWinDraft, plan: Any) -> None:
    failures = renderer_contract_hard_failures(draft, plan)
    if failures:
        raise RendererContractError(failures[0], failed_contracts=failures)


def renderer_contract_hard_failures(draft: DailyWinDraft, plan: Any) -> tuple[str, ...]:
    failures: list[str] = []
    if _three_concrete_cues_failed(draft, plan):
        failures.append(THREE_CONCRETE_CUES)
    if _diagnostic_order_failed(draft, plan):
        failures.append(DIAGNOSTIC_PROBE_BEFORE_TEACHING)
    if _canonical_assessment_failed(draft):
        failures.append(ONE_CANONICAL_ASSESSMENT)
    if _time_majority_failed(draft, plan):
        failures.append(PRIMARY_SKILL_TIME_MAJORITY)
    if _review_too_thin(draft, plan):
        failures.append(REVIEW_PRACTICE_THEN_CHECK)
    if _fresh_item_reused(draft, plan):
        failures.append(FRESH_ASSESSMENT_ITEM)
    if _age_respectful_failed(draft, plan):
        failures.append(AGE_RESPECTFUL_FOUNDATION)
    return tuple(failures)


def renderer_contract_soft_flags(draft: DailyWinDraft, plan: Any) -> tuple[str, ...]:
    flags: list[str] = []
    if _section_duration_implausible(draft):
        flags.append(SECTION_DURATION_IMPLAUSIBLE)
    if _growth_overlay_disconnected(draft, plan):
        flags.append(GROWTH_OVERLAY_DISCONNECTED)
    if _assessment_language_ambiguous(draft):
        flags.append(ASSESSMENT_LANGUAGE_AMBIGUOUS)
    return tuple(flags)


def _three_concrete_cues_failed(draft: DailyWinDraft, plan: Any) -> bool:
    if _field(plan, "scaffold_level") != "three_step_visual":
        return False
    learn = draft.segments[0]
    cues = [step.strip() for step in learn.steps if step.strip()]
    concrete = [step for step in cues if _looks_like_cue(step)]
    if len(concrete) >= 3:
        return False
    blob = " ".join([learn.title, *cues, draft.parent_briefing.how_to_coach])
    numbered = re.findall(r"(?:^|\n)\s*[1-3][.)]\s+\S+", blob)
    if len(numbered) >= 3:
        return False
    return True


def _looks_like_cue(step: str) -> bool:
    if _THREE_STEP_PROSE.search(step) and not _ACTION_START.match(step.strip()):
        return False
    if _ACTION_START.match(step.strip()):
        return True
    if re.match(r"^[1-3][.)]\s+\S+", step.strip()):
        return True
    return len(step.split()) <= 8


def _diagnostic_order_failed(draft: DailyWinDraft, plan: Any) -> bool:
    if _field(plan, "instruction_mode") != "diagnostic":
        return False
    learn_steps = list(draft.segments[0].steps)
    probe = _probe_task(plan)
    check_index = _first_check_index(learn_steps, probe)
    if check_index is None:
        return True
    for index, step in enumerate(learn_steps):
        if index < check_index and _is_teach_only(step):
            return True
    later = _segment_blob(draft.segments[1]) + " " + _segment_blob(draft.segments[2])
    return bool(_FINALISH.search(later))


def _first_check_index(steps: list[str], probe: str) -> int | None:
    probe_tokens = _tokens(probe)
    for index, step in enumerate(steps):
        if probe and probe_tokens and _tokens(step) & probe_tokens:
            return index
        if _CHECK.search(step):
            return index
    return None


def _is_teach_only(step: str) -> bool:
    return bool(_TEACH.search(step)) and not bool(_CHECK.search(step))


def _canonical_assessment_failed(draft: DailyWinDraft) -> bool:
    hits = 0
    if _FINALISH.search(draft.observation_focus):
        hits += 1
    for segment in draft.segments:
        if _FINALISH.search(_segment_blob(segment)):
            hits += 1
    blob = " ".join(
        [_segment_blob(segment) for segment in draft.segments]
        + [draft.observation_focus, *draft.success_checks]
    )
    if re.search(r"\btest this one too\b", blob, re.IGNORECASE):
        return True
    return hits >= 2


def _time_majority_failed(draft: DailyWinDraft, plan: Any) -> bool:
    learn, do, grow = draft.segments
    if learn.minutes + do.minutes <= grow.minutes:
        return True
    growth = _field(plan, "growth_target_code")
    primary = _field(plan, "primary_skill_code")
    if growth and is_academic_code(primary):
        if learn.minutes <= 5 and do.minutes >= 12:
            return True
        if grow.minutes >= 10 and grow.minutes > learn.minutes:
            return True
    return False


def _review_too_thin(draft: DailyWinDraft, plan: Any) -> bool:
    if _field(plan, "instruction_mode") != "review":
        return False
    learn = draft.segments[0]
    practice_steps = len(learn.steps)
    if practice_steps < 2:
        return True
    academic_steps = practice_steps + len(draft.segments[1].steps)
    if draft.duration_minutes >= 15 and academic_steps < 3:
        return True
    return False


def _fresh_item_reused(draft: DailyWinDraft, plan: Any) -> bool:
    primary = _field(plan, "primary_skill_code")
    if not _itemized(primary):
        return False
    learn_steps = list(draft.segments[0].steps)
    if len(learn_steps) < 2:
        return False
    practice_items = _extract_items(" ".join(learn_steps[:-1]))
    assess_items = _extract_items(learn_steps[-1])
    if not assess_items:
        assess_items = _extract_items(draft.observation_focus)
    if not practice_items or not assess_items:
        return False
    return bool(practice_items & assess_items)


def _section_duration_implausible(draft: DailyWinDraft) -> bool:
    total_words = 0
    for segment in draft.segments:
        words = sum(len(step.split()) for step in segment.steps)
        total_words += words
        if segment.minutes >= 8 and len(segment.steps) == 1 and words <= 12:
            return True
        if segment.minutes <= 3 and len(segment.steps) >= 4:
            return True
    return draft.duration_minutes >= 18 and total_words < 25


def _growth_overlay_disconnected(draft: DailyWinDraft, plan: Any) -> bool:
    growth = _field(plan, "growth_target_code")
    primary = _field(plan, "primary_skill_code")
    if not growth or not is_academic_code(primary):
        return False
    do_blob = _segment_blob(draft.segments[1]).lower()
    skill_tokens = {
        part
        for part in primary.lower().replace("_", ".").split(".")
        if part not in {"math", "reading", "writing", "within", "10", "20"}
    }
    if skill_tokens & _tokens(do_blob):
        return False
    play = {word for word in _tokens(do_blob) if word in _PLAY_TOKENS}
    return bool(play)


def _assessment_language_ambiguous(draft: DailyWinDraft) -> bool:
    if _canonical_assessment_failed(draft):
        return False
    practice_hits = 0
    check_hits = 0
    for segment in draft.segments:
        blob = _segment_blob(segment)
        if _PRACTICE_LABEL.search(blob):
            practice_hits += 1
        if _FINALISH.search(blob):
            check_hits += 1
    if _FINALISH.search(draft.observation_focus):
        check_hits += 1
    return check_hits >= 1 and practice_hits == 0


def _extract_items(text: str) -> set[str]:
    items = {match.group(1).strip().lower() for match in _QUOTED.finditer(text)}
    items.update(match.group(0).replace(" ", "") for match in _EQUATION.finditer(text))
    items.update(match.group(1).lower() for match in _CVC_WORD.finditer(text))
    return {item for item in items if item}


def _itemized(skill_code: str) -> bool:
    return any(skill_code.startswith(prefix) for prefix in _ITEMIZED_PREFIXES)


def _probe_task(plan: Any) -> str:
    probe = getattr(plan, "assessment_probe", None)
    if not isinstance(probe, dict):
        return ""
    return str(probe.get("observable_task") or "")


def _segment_blob(segment: Any) -> str:
    return " ".join([segment.title, *segment.steps, segment.parent_role])


def _field(plan: Any, name: str) -> str:
    value = getattr(plan, name, None)
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _age_respectful_failed(draft: DailyWinDraft, plan: Any) -> bool:
    if _field(plan, "presentation_constraint") != AGE_RESPECTFUL_FOUNDATION:
        contracts = getattr(plan, "renderer_contracts", None) or []
        if AGE_RESPECTFUL_FOUNDATION not in contracts:
            return False
    blob = " ".join(
        [_segment_blob(segment) for segment in draft.segments]
        + [
            draft.title,
            draft.objective,
            draft.observation_focus,
            *draft.success_checks,
            draft.parent_briefing.purpose,
            draft.parent_briefing.how_to_coach,
            draft.personalization_summary,
        ]
    )
    return bool(_BABY_TALK.search(blob))


def plan_with_contracts(plan: InstructionPlanContext) -> InstructionPlanContext:
    return plan.model_copy(
        update={"renderer_contracts": list(contracts_for_plan(plan))}
    )
