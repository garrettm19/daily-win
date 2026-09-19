import re
from collections import Counter
from dataclasses import dataclass

from daily_win_api.ai.providers.fake import FakeModelGateway, valid_daily_win_draft
from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.learning.enums import (
    AcademicBand,
    InstructionMode,
    ScaffoldLevel,
)
from daily_win_api.domains.learning.planner import InstructionPlan, plan_instruction
from daily_win_api.eval.builders import planner_input, state
from daily_win_api.eval.fixtures import load_eval_fixtures

_WORKSHEET = re.compile(
    r"\b(worksheet|circle the correct|fill in the blank|packet)\b",
    re.IGNORECASE,
)
_ANSWER_GIVING = re.compile(
    r"\b(the answer is|tell them it's|just say \d+|give them the answer)\b",
    re.IGNORECASE,
)
_FAKE_PRAISE = re.compile(
    r"\b(genius|so smart|gifted|natural talent|smart kid)\b",
    re.IGNORECASE,
)
_PERSONALITY = re.compile(
    r"\b(shy child|lazy|defiant|always anxious|problem child)\b",
    re.IGNORECASE,
)
_AFFECT = re.compile(
    r"\b(enjoy|fun|like|love|neat|tidy|handwriting|pretty|try hard|tried hard)\b",
    re.IGNORECASE,
)
_SCRIPTING = re.compile(r"\bSay:\s*[\"']", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "child",
        "parent",
        "with",
        "then",
        "this",
        "that",
        "from",
        "after",
        "first",
        "invite",
        "complete",
        "sentence",
        "activity",
        "practice",
        "before",
        "offering",
    }
)

PARENT_BURDEN_LIMITS = {
    "max_materials": 4,
    "max_steps": 10,
    "max_briefing_words": 120,
    "max_reflection_words": 40,
    "min_minutes": 10,
    "max_minutes": 25,
    "preferred_max_minutes": 20,
}


@dataclass(frozen=True)
class ParentBurden:
    briefing_words: int
    material_count: int
    step_count: int
    duration_minutes: int
    flags: tuple[str, ...]


@dataclass(frozen=True)
class DifficultyExample:
    id: str
    band: AcademicBand
    mode: InstructionMode
    scaffold: ScaffoldLevel
    label: str


def parent_burden(draft: DailyWinDraft) -> ParentBurden:
    briefing = " ".join(
        [
            draft.parent_briefing.purpose,
            draft.parent_briefing.how_to_coach,
            draft.parent_briefing.watch_for,
            draft.parent_briefing.avoid,
        ]
    )
    words = len(briefing.split())
    steps = sum(len(segment.steps) for segment in draft.segments)
    flags: list[str] = []
    if len(draft.materials) > PARENT_BURDEN_LIMITS["max_materials"]:
        flags.append("too_many_materials")
    if steps > PARENT_BURDEN_LIMITS["max_steps"]:
        flags.append("too_many_steps")
    if words > PARENT_BURDEN_LIMITS["max_briefing_words"]:
        flags.append("coaching_too_long")
    reflection_words = len(draft.observation_focus.split())
    if reflection_words > PARENT_BURDEN_LIMITS["max_reflection_words"]:
        flags.append("reflection_prompt_too_long")
    if not (
        PARENT_BURDEN_LIMITS["min_minutes"]
        <= draft.duration_minutes
        <= PARENT_BURDEN_LIMITS["max_minutes"]
    ):
        flags.append("duration_out_of_range")
    elif draft.duration_minutes > PARENT_BURDEN_LIMITS["preferred_max_minutes"]:
        flags.append("duration_longer_than_preferred")
    return ParentBurden(
        briefing_words=words,
        material_count=len(draft.materials),
        step_count=steps,
        duration_minutes=draft.duration_minutes,
        flags=tuple(flags),
    )


def anti_pattern_flags(draft: DailyWinDraft) -> tuple[str, ...]:
    blob = " ".join(
        [
            draft.title,
            draft.objective,
            draft.personalization_summary,
            draft.observation_focus,
            draft.parent_briefing.how_to_coach,
            *draft.success_checks,
            *[step for segment in draft.segments for step in segment.steps],
        ]
    )
    flags: list[str] = []
    if _WORKSHEET.search(blob):
        flags.append("worksheet_disguised_by_theme")
    if _ANSWER_GIVING.search(blob):
        flags.append("answer_giving_parent_prompts")
    if _FAKE_PRAISE.search(blob):
        flags.append("fake_praise")
    if _PERSONALITY.search(blob):
        flags.append("personality_labels")
    if _SCRIPTING.search(blob) or len(draft.parent_briefing.how_to_coach.split()) > 80:
        flags.append("excessive_parent_scripting")
    if _AFFECT.search(" ".join([draft.observation_focus, *draft.success_checks])):
        flags.append("assessment_wrong_construct")
    counts = Counter(
        word
        for word in re.findall(r"[a-z]{4,}", blob.lower())
        if word not in _STOPWORDS
    )
    if any(count >= 6 for count in counts.values()):
        flags.append("forced_interest_references")
    if len(draft.supporting_skill_codes) > 2:
        flags.append("too_many_skills")
    if draft.primary_skill_code in draft.supporting_skill_codes:
        flags.append("duplicate_skill_codes")
    return tuple(flags)


def difficulty_examples() -> tuple[DifficultyExample, ...]:
    return (
        DifficultyExample(
            "introduce_high_not_observed",
            AcademicBand.NOT_OBSERVED,
            InstructionMode.INTRODUCE,
            ScaffoldLevel.HIGH,
            "appropriate",
        ),
        DifficultyExample(
            "practice_medium_developing",
            AcademicBand.DEVELOPING,
            InstructionMode.PRACTICE,
            ScaffoldLevel.MEDIUM,
            "appropriate",
        ),
        DifficultyExample(
            "independent_try_not_observed",
            AcademicBand.NOT_OBSERVED,
            InstructionMode.INTRODUCE,
            ScaffoldLevel.LOW,
            "too_hard",
        ),
        DifficultyExample(
            "high_scaffold_retained",
            AcademicBand.RETAINED,
            InstructionMode.PRACTICE,
            ScaffoldLevel.HIGH,
            "too_easy",
        ),
        DifficultyExample(
            "review_medium_demonstrated",
            AcademicBand.DEMONSTRATED,
            InstructionMode.REVIEW,
            ScaffoldLevel.MEDIUM,
            "appropriate",
        ),
        DifficultyExample(
            "diagnostic_medium_not_observed",
            AcademicBand.NOT_OBSERVED,
            InstructionMode.DIAGNOSTIC,
            ScaffoldLevel.MEDIUM,
            "appropriate",
        ),
    )


def planner_difficulty_label(
    band: AcademicBand, mode: InstructionMode, scaffold: ScaffoldLevel
) -> str:
    if scaffold is ScaffoldLevel.LOW and band in {
        AcademicBand.NOT_OBSERVED,
        AcademicBand.EMERGING,
    }:
        return "too_hard"
    if (
        scaffold is ScaffoldLevel.HIGH
        and band in {AcademicBand.DEMONSTRATED, AcademicBand.RETAINED}
        and mode is not InstructionMode.REMEDIATION
    ):
        return "too_easy"
    return "appropriate"


def theme_variants_keep_instruction() -> list[str]:
    errors: list[str] = []
    soccer = plan_instruction(
        planner_input(
            interests=("soccer",),
            goals=(("writing.organization", 1),),
            states=(
                state(
                    "writing.sentences.complete_sentence",
                    AcademicBand.DEMONSTRATED,
                    sessions=3,
                ),
            ),
        )
    )
    space = plan_instruction(
        planner_input(
            interests=("space",),
            goals=(("writing.organization", 1),),
            states=(
                state(
                    "writing.sentences.complete_sentence",
                    AcademicBand.DEMONSTRATED,
                    sessions=3,
                ),
            ),
        )
    )
    animals = plan_instruction(
        planner_input(
            interests=("animals",),
            goals=(("writing.organization", 1),),
            states=(
                state(
                    "writing.sentences.complete_sentence",
                    AcademicBand.DEMONSTRATED,
                    sessions=3,
                ),
            ),
        )
    )
    plans = (soccer, space, animals)
    skills = {item.primary_skill_code for item in plans}
    probes = {item.assessment_probe.get("target_skill_code") for item in plans}
    objectives = {item.assessment_objective for item in plans}
    if len(skills) != 1 or len(probes) != 1 or len(objectives) != 1:
        errors.append("theme variants changed instructional objective")
    themes = {item.engagement_theme_constraints for item in plans}
    if len(themes) != 3:
        errors.append("theme constraints did not vary with interests")
    drafts = [
        _themed_draft(soccer, title)
        for title in (
            "Soccer sequencing cards",
            "Space sequencing cards",
            "Animal sequencing cards",
        )
    ]
    if len({item.objective for item in drafts}) != 1:
        errors.append("rendered objective changed with theme")
    if len({tuple(item.success_checks) for item in drafts}) != 1:
        errors.append("success criteria changed with theme")
    if len({item.primary_skill_code for item in drafts}) != 1:
        errors.append("rendered skill changed with theme")
    return errors


def _themed_draft(plan: InstructionPlan, title: str) -> DailyWinDraft:
    base = valid_daily_win_draft(primary_skill_code=plan.primary_skill_code)
    expected = str(
        plan.assessment_probe.get("expected_outcome") or plan.assessment_objective
    )
    return base.model_copy(
        update={
            "title": title,
            "objective": plan.assessment_objective,
            "success_checks": [expected],
            "personalization_summary": f"Theme: {title}",
        }
    )


def labelled_anti_pattern_drafts() -> tuple[tuple[str, DailyWinDraft, str | None], ...]:
    clean = valid_daily_win_draft()
    worksheet = clean.model_copy(
        update={"objective": "Complete the worksheet packet of addition facts."}
    )
    answer = clean.model_copy(
        update={
            "parent_briefing": clean.parent_briefing.model_copy(
                update={"how_to_coach": "If they stall, tell them the answer is 8."}
            )
        }
    )
    praise = clean.model_copy(
        update={"personalization_summary": "Call the child a genius and gifted."}
    )
    personality = clean.model_copy(
        update={"title": "Help the shy child stop being a problem child"}
    )
    scripting = clean.model_copy(
        update={
            "parent_briefing": clean.parent_briefing.model_copy(
                update={
                    "how_to_coach": (
                        'Say: "The first number is 4." '
                        'Say: "Now add 3." Say: "Write 7."'
                    )
                }
            )
        }
    )
    forced = clean.model_copy(
        update={
            "personalization_summary": (
                "soccer soccer soccer soccer soccer soccer theme stuffing"
            )
        }
    )
    wrong_probe = clean.model_copy(
        update={
            "observation_focus": "Did the child enjoy the story?",
            "success_checks": ["Did the child write neatly?"],
        }
    )
    too_many = clean.model_copy(
        update={
            "supporting_skill_codes": [
                "math.addition.within_10",
                "reading.fluency.smooth_oral",
                "writing.spelling.high_frequency",
            ]
        }
    )
    return (
        ("clean", clean, None),
        ("worksheet_disguised_by_theme", worksheet, "worksheet_disguised_by_theme"),
        ("answer_giving_parent_prompts", answer, "answer_giving_parent_prompts"),
        ("fake_praise", praise, "fake_praise"),
        ("personality_labels", personality, "personality_labels"),
        ("excessive_parent_scripting", scripting, "excessive_parent_scripting"),
        ("forced_interest_references", forced, "forced_interest_references"),
        ("assessment_wrong_construct", wrong_probe, "assessment_wrong_construct"),
        ("too_many_skills", too_many, "too_many_skills"),
    )


def fake_render_structural_errors() -> list[str]:
    from daily_win_api.eval.scoring import score_generation

    fixture = next(item for item in load_eval_fixtures() if item.id == "hayes_first")
    generated = FakeModelGateway().generate_daily_win(fixture.context)
    scored = score_generation(fixture, generated)
    errors = [check.name for check in scored.checks if not check.passed]
    plan = fixture.context.instruction_plan
    if generated.draft.primary_skill_code != plan.primary_skill_code:
        errors.append("target_skill_fidelity")
    task = str(plan.assessment_probe.get("observable_task") or "")
    if task and task not in generated.draft.observation_focus:
        errors.append("assessment_fidelity")
    errors.extend(parent_burden(generated.draft).flags)
    errors.extend(anti_pattern_flags(generated.draft))
    return errors
