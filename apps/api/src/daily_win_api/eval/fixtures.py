from dataclasses import dataclass
from datetime import UTC, datetime

from daily_win_api.ai.schemas import (
    AdaptationDirective,
    DailyWinModelContext,
    EvidenceSummaryContext,
    GoalContext,
    InstructionPlanContext,
    LearningEventContext,
    Material,
    ParentReportedBaselineContext,
    PriorDailyWinContext,
    SkillStateContext,
)
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS

ALLOWED_SKILL_CODES = [item["code"] for item in SKILL_DEFINITIONS]
ALLOWED_MATERIALS = [material.value for material in Material]

EVENT_PROMPT = (
    "Most recent parent observation for growth.persistence: "
    "child returned to the task after one prompt."
)
EVENT_INDEPENDENT = (
    "Most recent parent observation for growth.persistence: "
    "child returned to the task independently."
)
EVENT_SUPPORT = (
    "Most recent parent observation for growth.persistence: "
    "child needed significant help after a setback."
)
EVENT_STOPPED = (
    "Most recent parent observation for growth.persistence: "
    "child stopped or avoided after a setback."
)


@dataclass(frozen=True)
class EvalFixture:
    id: str
    label: str
    support: str
    win_kind: str
    context: DailyWinModelContext


def _goal(priority: int, code: str, display_name: str, domain: str) -> GoalContext:
    return GoalContext(
        priority=priority,
        skill_code=code,
        display_name=display_name,
        domain=domain,
    )


def _directive(signal: str, nickname: str, challenge: str, coaching: str, summary: str):
    return AdaptationDirective(
        skill_code="growth.persistence",
        latest_signal=signal,
        challenge_adjustment=challenge,
        coaching_adjustment=coaching,
        parent_facing_summary=summary.format(nickname=nickname),
    )


def _event(summary: str, skill_code: str | None = "growth.persistence"):
    return LearningEventContext(
        evidence_kind="OBSERVATION",
        source="PARENT",
        event_type="skill_observation",
        skill_code=skill_code,
        occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        summary=summary,
    )


def _prior(title: str, skill: str, objective: str) -> PriorDailyWinContext:
    return PriorDailyWinContext(
        title=title, primary_skill_code=skill, objective=objective
    )


def _state(
    code: str,
    *,
    signal: str | None,
    direction: str | None,
    evidence_count: int,
    summary: str | None,
) -> SkillStateContext:
    return SkillStateContext(
        skill_code=code,
        evidence_count=evidence_count,
        confidence=0.4 if evidence_count else None,
        has_derived_state=bool(signal),
        latest_signal=signal,
        direction=direction,
        summary=summary,
    )


def _context(
    *,
    nickname: str,
    age_years: int,
    grade: str,
    interests: list[str],
    strengths: list[str],
    difficulties: list[str],
    motivators: list[str],
    response: str,
    minutes: int,
    goals: list[GoalContext],
    states: list[SkillStateContext],
    events: list[LearningEventContext],
    priors: list[PriorDailyWinContext],
    directive: AdaptationDirective,
) -> DailyWinModelContext:
    del states
    return DailyWinModelContext(
        nickname=nickname,
        parent_reported_baseline=ParentReportedBaselineContext(
            age_years=age_years,
            grade=grade,
            interests=interests,
            strengths=strengths,
            current_difficulties=difficulties,
            motivators=motivators,
            response_to_difficulty=response,
            preferred_activity_minutes=minutes,
        ),
        instruction_plan=_plan_from_goals(goals, directive, priors, minutes, interests),
        bounded_evidence_summaries=[
            EvidenceSummaryContext(
                skill_code=event.skill_code or "unspecified",
                summary=event.summary,
                reporting_kind="parent_reported",
            )
            for event in events[:6]
        ],
        recent_themes=[prior.title for prior in priors[:3]],
        allowed_skill_codes=ALLOWED_SKILL_CODES,
        allowed_materials=ALLOWED_MATERIALS,
    )


def _plan_from_goals(
    goals: list[GoalContext],
    directive: AdaptationDirective,
    priors: list[PriorDailyWinContext],
    minutes: int,
    interests: list[str],
) -> InstructionPlanContext:
    primary = goals[0].skill_code
    supporting = goals[1].skill_code if len(goals) > 1 else None
    growth = next(
        (
            goal.skill_code
            for goal in goals
            if goal.skill_code.startswith(("growth.", "life."))
        ),
        None,
    )
    summary = (
        directive.parent_facing_summary
        if directive.latest_signal != "no_signal"
        else None
    )
    return InstructionPlanContext(
        primary_skill_code=primary,
        supporting_skill_code=supporting,
        selection_reason_codes=["parent_priority", "eval_fixture"],
        instruction_mode="practice",
        intended_difficulty="similar",
        scaffold_level="one_prompt",
        prerequisite_rationale="Eval fixture plan.",
        assessment_objective="Observe one independent try at the planned skill.",
        assessment_probe={
            "target_skill_code": primary,
            "probe_type": "observe_independent_try",
            "observable_task": "Invite one independent try.",
            "expected_outcome": "The child attempts the planned skill.",
            "success_criteria": "Independent correct attempt.",
            "allowed_support": "One light prompt after an independent try.",
        },
        desired_evidence="structured academic result plus parent observation",
        growth_target_code=growth,
        growth_adaptation_summary=summary,
        duration_minutes=minutes,
        engagement_theme_constraints=interests[:2],
        recent_themes_to_avoid=[prior.title for prior in priors[:3]],
        policy_version="instruction_policy_v1",
        academic_band="not_observed",
    )


def load_eval_fixtures() -> list[EvalFixture]:
    """Synthetic children only. Never load real child data."""
    persistence = _goal(1, "growth.persistence", "Persistence", "GROWTH")
    writing = _goal(2, "writing.sentences", "Sentences", "WRITING")
    independence = _goal(3, "growth.independence", "Independence", "GROWTH")
    reading = _goal(1, "reading.comprehension", "Comprehension", "READING")
    math_add = _goal(1, "math.addition", "Addition", "MATH")
    writing_org = _goal(1, "writing.organization", "Organization", "WRITING")
    phonics = _goal(1, "reading.phonics", "Phonics", "READING")
    number = _goal(1, "math.number_sense", "Number sense", "MATH")

    def none_dir(nick: str) -> AdaptationDirective:
        return _directive(
            "no_signal",
            nick,
            "none",
            "No persistence-specific adjustment.",
            "No persistence-specific adjustment from the last activity.",
        )

    def prompt_dir(nick: str) -> AdaptationDirective:
        return _directive(
            "retry_after_prompt",
            nick,
            "similar",
            "Offer one light prompt, then give space.",
            (
                "Last time, {nickname} returned after one prompt. "
                "Today, keep the challenge similar."
            ),
        )

    def independent_dir(nick: str) -> AdaptationDirective:
        return _directive(
            "independent_retry",
            nick,
            "slightly_increase",
            "Wait longer before helping.",
            (
                "Last time, {nickname} returned independently. "
                "Today, raise the challenge slightly."
            ),
        )

    def support_dir(nick: str) -> AdaptationDirective:
        return _directive(
            "significant_support",
            nick,
            "reduce",
            "Offer a clearer first scaffold and keep the retry small.",
            (
                "Last time, {nickname} needed significant help. "
                "Today, simplify the first step."
            ),
        )

    def stop_dir(nick: str) -> AdaptationDirective:
        return _directive(
            "disengaged_after_setback",
            nick,
            "shorten",
            "Make the first retry easier and prioritize re-entry.",
            (
                "Last time, {nickname} stopped after a setback. "
                "Today, shorten the challenge."
            ),
        )

    specs: list[tuple[str, str, str, str, DailyWinModelContext]] = [
        (
            "hayes_first",
            "Hayes first Win, persistence, medium support",
            "medium",
            "first",
            _context(
                nickname="Hayes",
                age_years=7,
                grade="1",
                interests=["building things", "soccer", "Minecraft"],
                strengths=["math", "reading"],
                difficulties=["writing", "persistence after an initial failure"],
                motivators=["competition", "short challenges"],
                response="becomes frustrated after the first failure",
                minutes=20,
                goals=[persistence, writing, independence],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Hayes"),
            ),
        ),
        (
            "hayes_adaptive_prompt",
            "Hayes adaptive Win after a prompted retry",
            "medium",
            "adaptive",
            _context(
                nickname="Hayes",
                age_years=7,
                grade="1",
                interests=["building things", "soccer"],
                strengths=["math"],
                difficulties=["writing"],
                motivators=["short challenges"],
                response="needs one prompt after a miss",
                minutes=20,
                goals=[persistence, writing, independence],
                states=[
                    _state(
                        "growth.persistence",
                        signal="retry_after_prompt",
                        direction="stable",
                        evidence_count=1,
                        summary="Returned after one prompt.",
                    )
                ],
                events=[_event(EVENT_PROMPT)],
                priors=[
                    _prior(
                        "Build, miss, try again",
                        "growth.persistence",
                        "Stay with a wobble.",
                    )
                ],
                directive=prompt_dir("Hayes"),
            ),
        ),
        (
            "age5_reading_first",
            "Age 5 reading first Win, low support",
            "low",
            "first",
            _context(
                nickname="River",
                age_years=5,
                grade="K",
                interests=["dinosaurs", "drawing"],
                strengths=["curiosity"],
                difficulties=["sitting still", "letter sounds"],
                motivators=["stickers", "short games"],
                response="asks to stop quickly",
                minutes=12,
                goals=[
                    phonics,
                    persistence,
                    _goal(3, "math.number_sense", "Number sense", "MATH"),
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("River"),
            ),
        ),
        (
            "age6_math_high_support",
            "Age 6 math with high support after disengagement",
            "high",
            "adaptive",
            _context(
                nickname="Sasha",
                age_years=6,
                grade="1",
                interests=["soccer", "dogs"],
                strengths=["counting"],
                difficulties=["addition", "waiting"],
                motivators=["movement", "being first"],
                response="walks away after a miss",
                minutes=15,
                goals=[math_add, persistence, independence],
                states=[
                    _state(
                        "growth.persistence",
                        signal="disengaged_after_setback",
                        direction="needs_support",
                        evidence_count=2,
                        summary="Stopped after a setback.",
                    )
                ],
                events=[_event(EVENT_STOPPED)],
                priors=[
                    _prior(
                        "Count and kick",
                        "math.addition",
                        "Add two small numbers, then kick a soft ball.",
                    )
                ],
                directive=stop_dir("Sasha"),
            ),
        ),
        (
            "age8_writing_independent",
            "Age 8 writing after independent retry",
            "low",
            "adaptive",
            _context(
                nickname="Quinn",
                age_years=8,
                grade="3",
                interests=["Minecraft", "comic books"],
                strengths=["reading", "ideas"],
                difficulties=["organizing writing"],
                motivators=["making comics", "choice"],
                response="tries again with a new idea",
                minutes=20,
                goals=[writing_org, persistence, reading],
                states=[
                    _state(
                        "growth.persistence",
                        signal="independent_retry",
                        direction="improving",
                        evidence_count=3,
                        summary="Returned independently.",
                    )
                ],
                events=[_event(EVENT_INDEPENDENT)],
                priors=[
                    _prior(
                        "One panel story",
                        "writing.organization",
                        "Write a beginning and an ending.",
                    )
                ],
                directive=independent_dir("Quinn"),
            ),
        ),
        (
            "age9_reading_medium",
            "Age 9 comprehension, medium support",
            "medium",
            "first",
            _context(
                nickname="Eden",
                age_years=9,
                grade="4",
                interests=["space", "basketball"],
                strengths=["vocabulary", "sports"],
                difficulties=["finding the main idea"],
                motivators=["facts", "friendly competition"],
                response="rereads when asked",
                minutes=22,
                goals=[reading, persistence, writing],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Eden"),
            ),
        ),
        (
            "age7_math_first",
            "Age 7 number sense first Win",
            "medium",
            "first",
            _context(
                nickname="Noor",
                age_years=7,
                grade="2",
                interests=["cooking play", "blocks"],
                strengths=["sharing"],
                difficulties=["place value"],
                motivators=["helping", "timer races"],
                response="asks for the answer",
                minutes=18,
                goals=[number, persistence, independence],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Noor"),
            ),
        ),
        (
            "age5_persistence_high",
            "Age 5 persistence after significant support",
            "high",
            "adaptive",
            _context(
                nickname="Remy",
                age_years=5,
                grade="K",
                interests=["trucks", "songs"],
                strengths=["memory for songs"],
                difficulties=["waiting", "trying a second time"],
                motivators=["music", "parent nearby"],
                response="needs a lot of help after a miss",
                minutes=12,
                goals=[persistence, phonics, independence],
                states=[
                    _state(
                        "growth.persistence",
                        signal="significant_support",
                        direction="needs_support",
                        evidence_count=1,
                        summary="Needed significant help.",
                    )
                ],
                events=[_event(EVENT_SUPPORT)],
                priors=[
                    _prior(
                        "Song and stack",
                        "growth.persistence",
                        "Stack two cups, then try again.",
                    )
                ],
                directive=support_dir("Remy"),
            ),
        ),
        (
            "age6_writing_first",
            "Age 6 sentences first Win",
            "medium",
            "first",
            _context(
                nickname="Blake",
                age_years=6,
                grade="1",
                interests=["cats", "stickers"],
                strengths=["talking about ideas"],
                difficulties=["writing a full sentence"],
                motivators=["stickers", "being read to"],
                response="erases and stops",
                minutes=15,
                goals=[writing, persistence, phonics],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Blake"),
            ),
        ),
        (
            "age8_math_adaptive",
            "Age 8 addition after prompted retry",
            "medium",
            "adaptive",
            _context(
                nickname="Kai",
                age_years=8,
                grade="3",
                interests=["Lego", "soccer"],
                strengths=["building", "sports"],
                difficulties=["multi-digit addition"],
                motivators=["building something real"],
                response="returns after one hint",
                minutes=20,
                goals=[math_add, persistence, independence],
                states=[
                    _state(
                        "growth.persistence",
                        signal="retry_after_prompt",
                        direction="stable",
                        evidence_count=2,
                        summary="Returned after one prompt.",
                    )
                ],
                events=[_event(EVENT_PROMPT)],
                priors=[
                    _prior(
                        "Lego plus two",
                        "math.addition",
                        "Add two small groups of bricks.",
                    )
                ],
                directive=prompt_dir("Kai"),
            ),
        ),
        (
            "age9_independence_first",
            "Age 9 independence first Win",
            "low",
            "first",
            _context(
                nickname="Sage",
                age_years=9,
                grade="4",
                interests=["gardening", "drawing"],
                strengths=["planning"],
                difficulties=["starting without being told"],
                motivators=["choice", "real jobs"],
                response="waits for instructions",
                minutes=22,
                goals=[
                    _goal(1, "growth.independence", "Independence", "GROWTH"),
                    writing,
                    math_add,
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Sage"),
            ),
        ),
        (
            "age7_reading_adaptive",
            "Age 7 fluency after independent retry",
            "low",
            "adaptive",
            _context(
                nickname="Jordan",
                age_years=7,
                grade="2",
                interests=["jokes", "running"],
                strengths=["phonics"],
                difficulties=["smooth reading"],
                motivators=["making someone laugh"],
                response="tries the line again alone",
                minutes=18,
                goals=[
                    _goal(1, "reading.fluency", "Fluency", "READING"),
                    persistence,
                    writing,
                ],
                states=[
                    _state(
                        "growth.persistence",
                        signal="independent_retry",
                        direction="improving",
                        evidence_count=2,
                        summary="Returned independently.",
                    )
                ],
                events=[_event(EVENT_INDEPENDENT)],
                priors=[
                    _prior(
                        "Read it like a joke",
                        "reading.fluency",
                        "Read one short joke twice.",
                    )
                ],
                directive=independent_dir("Jordan"),
            ),
        ),
        (
            "age5_math_first",
            "Age 5 number sense, low support",
            "low",
            "first",
            _context(
                nickname="Pax",
                age_years=5,
                grade="K",
                interests=["trains", "blocks"],
                strengths=["sorting"],
                difficulties=["counting past ten"],
                motivators=["lining things up"],
                response="starts over happily",
                minutes=12,
                goals=[number, persistence, phonics],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Pax"),
            ),
        ),
        (
            "age8_high_support_writing",
            "Age 8 writing after disengagement",
            "high",
            "adaptive",
            _context(
                nickname="Reese",
                age_years=8,
                grade="3",
                interests=["animals", "origami"],
                strengths=["drawing"],
                difficulties=["finishing a paragraph"],
                motivators=["animals", "folding paper"],
                response="crumples the paper",
                minutes=18,
                goals=[writing_org, persistence, independence],
                states=[
                    _state(
                        "growth.persistence",
                        signal="disengaged_after_setback",
                        direction="needs_support",
                        evidence_count=2,
                        summary="Stopped after a setback.",
                    )
                ],
                events=[_event(EVENT_STOPPED)],
                priors=[
                    _prior(
                        "Animal beginning",
                        "writing.organization",
                        "Write one opening sentence.",
                    )
                ],
                directive=stop_dir("Reese"),
            ),
        ),
        (
            "age6_reading_first",
            "Age 6 comprehension first Win",
            "medium",
            "first",
            _context(
                nickname="Nico",
                age_years=6,
                grade="1",
                interests=["ocean", "puzzles"],
                strengths=["listening"],
                difficulties=["retelling a story"],
                motivators=["pictures", "being right"],
                response="guesses quickly",
                minutes=15,
                goals=[reading, persistence, number],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Nico"),
            ),
        ),
        (
            "age9_math_high",
            "Age 9 multiplication after significant support",
            "high",
            "adaptive",
            _context(
                nickname="Dana",
                age_years=9,
                grade="4",
                interests=["music", "cooking play"],
                strengths=["patterns"],
                difficulties=["times tables"],
                motivators=["songs", "kitchen tools that are safe"],
                response="needs the first example done together",
                minutes=22,
                goals=[
                    _goal(1, "math.multiplication", "Multiplication", "MATH"),
                    persistence,
                    independence,
                ],
                states=[
                    _state(
                        "growth.persistence",
                        signal="significant_support",
                        direction="needs_support",
                        evidence_count=3,
                        summary="Needed significant help.",
                    )
                ],
                events=[_event(EVENT_SUPPORT)],
                priors=[
                    _prior(
                        "Equal groups of spoons",
                        "math.multiplication",
                        "Make two equal groups.",
                    )
                ],
                directive=support_dir("Dana"),
            ),
        ),
        (
            "age7_writing_first",
            "Age 7 spelling first Win",
            "medium",
            "first",
            _context(
                nickname="Ari",
                age_years=7,
                grade="2",
                interests=["superheroes", "soccer"],
                strengths=["story ideas"],
                difficulties=["spelling common words"],
                motivators=["heroes", "moving"],
                response="asks how to spell everything",
                minutes=18,
                goals=[
                    _goal(1, "writing.spelling", "Spelling", "WRITING"),
                    persistence,
                    math_add,
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Ari"),
            ),
        ),
        (
            "age8_reading_prompt",
            "Age 8 vocabulary after prompted retry",
            "medium",
            "adaptive",
            _context(
                nickname="Rowan",
                age_years=8,
                grade="3",
                interests=["nature", "comics"],
                strengths=["curiosity"],
                difficulties=["new word meanings"],
                motivators=["collecting facts"],
                response="tries again after one hint",
                minutes=20,
                goals=[
                    _goal(1, "reading.vocabulary", "Vocabulary", "READING"),
                    persistence,
                    writing,
                ],
                states=[
                    _state(
                        "growth.persistence",
                        signal="retry_after_prompt",
                        direction="stable",
                        evidence_count=1,
                        summary="Returned after one prompt.",
                    )
                ],
                events=[_event(EVENT_PROMPT)],
                priors=[
                    _prior(
                        "New nature word",
                        "reading.vocabulary",
                        "Use one new word in a sentence.",
                    )
                ],
                directive=prompt_dir("Rowan"),
            ),
        ),
        (
            "age6_independence_adaptive",
            "Age 6 independence after independent retry",
            "low",
            "adaptive",
            _context(
                nickname="Ellis",
                age_years=6,
                grade="1",
                interests=["blocks", "pretend store"],
                strengths=["talking"],
                difficulties=["choosing the next step"],
                motivators=["pretend play"],
                response="picks a next step after one miss",
                minutes=15,
                goals=[independence, persistence, number],
                states=[
                    _state(
                        "growth.persistence",
                        signal="independent_retry",
                        direction="improving",
                        evidence_count=1,
                        summary="Returned independently.",
                    )
                ],
                events=[_event(EVENT_INDEPENDENT)],
                priors=[
                    _prior(
                        "Choose the next block",
                        "growth.independence",
                        "Pick the next piece without being told.",
                    )
                ],
                directive=independent_dir("Ellis"),
            ),
        ),
        (
            "age9_writing_first",
            "Age 9 sentences first Win, low support",
            "low",
            "first",
            _context(
                nickname="Shay",
                age_years=9,
                grade="4",
                interests=["history facts", "drawing maps"],
                strengths=["reading"],
                difficulties=["clear sentences"],
                motivators=["maps", "being accurate"],
                response="rewrites without being asked",
                minutes=22,
                goals=[writing, persistence, reading],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Shay"),
            ),
        ),
        (
            "nova_first",
            "Nova first Win, writing organization",
            "medium",
            "first",
            _context(
                nickname="Nova",
                age_years=8,
                grade="3",
                interests=["space", "drawing"],
                strengths=["reading"],
                difficulties=["organizing writing"],
                motivators=["stories/imagination", "choice"],
                response="asks for help quickly",
                minutes=20,
                goals=[
                    writing_org,
                    _goal(2, "growth.persistence", "Persistence", "GROWTH"),
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Nova"),
            ),
        ),
        (
            "milo_first",
            "Milo first Win, number sense",
            "medium",
            "first",
            _context(
                nickname="Milo",
                age_years=6,
                grade="1",
                interests=["dinosaurs", "soccer"],
                strengths=["communication"],
                difficulties=["starting independently", "number sense"],
                motivators=["movement", "short challenges"],
                response="keeps trying independently",
                minutes=15,
                goals=[
                    number,
                    _goal(2, "growth.independence", "Independence", "GROWTH"),
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Milo"),
            ),
        ),
        (
            "riley_first",
            "Riley first Win, reading comprehension",
            "low",
            "first",
            _context(
                nickname="Riley",
                age_years=9,
                grade="4",
                interests=["music", "building"],
                strengths=["math"],
                difficulties=["understanding what was read"],
                motivators=["building/making something", "choice"],
                response="becomes frustrated after an initial failure",
                minutes=25,
                goals=[
                    reading,
                    _goal(2, "growth.problem_solving", "Problem solving", "GROWTH"),
                ],
                states=[],
                events=[],
                priors=[],
                directive=none_dir("Riley"),
            ),
        ),
    ]

    return [
        EvalFixture(
            id=item_id,
            label=label,
            support=support,
            win_kind=win_kind,
            context=context,
        )
        for item_id, label, support, win_kind, context in specs
    ]
