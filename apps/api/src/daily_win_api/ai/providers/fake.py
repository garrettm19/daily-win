from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import (
    Adaptations,
    DailyWinDraft,
    DailyWinGenerationResult,
    DailyWinModelContext,
    DailyWinSegment,
    InstructionPlanContext,
    Material,
    ParentBriefing,
    SegmentType,
)


def valid_daily_win_draft(
    *,
    primary_skill_code: str = "growth.persistence",
    supporting_skill_codes: list[str] | None = None,
    title: str = "Build, miss, try again",
    extra_step: str | None = None,
    materials: list[Material] | None = None,
    safety_flags: list[str] | None = None,
    adaptation_summary: str | None = None,
) -> DailyWinDraft:
    learn_steps = [
        "Show two simple addition problems on paper.",
        "Invite the child to try the first one independently.",
    ]
    do_steps = [
        "Build a short block tower together, then knock it gently and rebuild once.",
    ]
    grow_steps = [
        "After the first rebuild wobble, pause and ask what to try next.",
        "Celebrate one specific effort, not the perfect tower.",
    ]
    learn_title = "Two quick number tries"
    do_title = "Tower, wobble, rebuild"
    grow_title = "Stay with the second try"
    if extra_step:
        grow_steps.append(extra_step)
    if title == "One sentence, then try again":
        learn_steps = [
            "Ask the child to say one complete sentence about a favorite game.",
            "Invite one independent rewrite if the first try is incomplete.",
        ]
        do_steps = [
            "Act out the sentence with a quiet indoor movement, then freeze.",
        ]
        grow_steps = [
            "If the first try stalls, wait, then offer one prompt and give space.",
        ]
        learn_title = "One complete sentence"
        do_title = "Act it out, then freeze"
        grow_title = "Stay with the second try"

    return DailyWinDraft(
        title=title,
        objective="Practice staying with a challenge after the first unsuccessful try.",
        duration_minutes=18,
        primary_skill_code=primary_skill_code,
        supporting_skill_codes=supporting_skill_codes or ["math.addition"],
        personalization_summary=(
            "Uses a short building challenge and a tiny math try, matching the "
            "parent-reported interest in building things and the persistence goal."
        ),
        materials=materials
        or [Material.PAPER, Material.PENCIL, Material.BLOCKS, Material.TIMER],
        parent_briefing=ParentBriefing(
            purpose="Help the child stay with a task after the first miss.",
            how_to_coach="Wait before offering a hint. Name the effort you see.",
            watch_for="What happens right after the first unsuccessful attempt.",
            avoid="Do not jump in with the answer or treat a wobble as failure.",
        ),
        segments=[
            DailyWinSegment(
                type=SegmentType.LEARN,
                title=learn_title,
                minutes=6,
                steps=learn_steps,
                parent_role="Sit beside, not in front. Offer a hint only if asked.",
            ),
            DailyWinSegment(
                type=SegmentType.DO,
                title=do_title,
                minutes=7,
                steps=do_steps,
                parent_role="Keep the space calm and the rebuild optional once.",
            ),
            DailyWinSegment(
                type=SegmentType.GROW,
                title=grow_title,
                minutes=5,
                steps=grow_steps,
                parent_role="Notice effort. Do not rescue immediately.",
            ),
        ],
        adaptations=Adaptations(
            if_too_easy="Use a slightly taller tower or a third math try.",
            if_too_hard="Do the first rebuild together, then invite one solo block.",
        ),
        success_checks=[
            "The child makes a second attempt after the first miss.",
            "The parent waits before giving the answer.",
            "The activity stays under about 20 minutes.",
        ],
        observation_focus=(
            "Notice what the child does after the first unsuccessful attempt."
        ),
        safety_flags=safety_flags or [],
        adaptation_summary=adaptation_summary,
    )


def adaptive_daily_win_draft(nickname: str = "the child") -> DailyWinDraft:
    draft = valid_daily_win_draft(
        title="One sentence, then try again",
        supporting_skill_codes=["writing.sentences"],
        adaptation_summary=(
            f"Last time, {nickname} rejoined after one prompt. This activity "
            "keeps the challenge similar but asks you to wait a little longer "
            "before helping."
        ),
    )
    return draft.model_copy(
        update={
            "personalization_summary": (
                "Uses a short sentence try after a stall, matching the "
                "persistence goal without repeating the previous building activity."
            ),
            "parent_briefing": ParentBriefing(
                purpose="Help the child stay with a short writing try after a stall.",
                how_to_coach="Wait before offering a hint. Name the effort you see.",
                watch_for="What happens right after the first incomplete try.",
                avoid="Do not jump in with the sentence or treat a stall as failure.",
            ),
            "adaptations": Adaptations(
                if_too_easy="Ask for a second sentence with more detail.",
                if_too_hard=(
                    "Offer a starter phrase, then invite one independent finish."
                ),
            ),
        }
    )


class FakeModelGateway:
    """Injectable test double. Not a production provider."""

    def __init__(
        self,
        draft: DailyWinDraft | None = None,
        error: Exception | None = None,
        provider: str = "fake",
        model: str = "fake-model",
        adaptive_draft: DailyWinDraft | None = None,
        *,
        align_to_plan: bool = True,
    ) -> None:
        self.draft = draft or valid_daily_win_draft()
        self.adaptive_draft = adaptive_draft
        self.error = error
        self.provider = provider
        self.model = model
        self.align_to_plan = align_to_plan
        self.calls: list[DailyWinModelContext] = []

    def generate_daily_win(
        self, context: DailyWinModelContext
    ) -> DailyWinGenerationResult:
        self.calls.append(context)
        if self.error is not None:
            raise self.error
        draft = self.draft
        plan = context.instruction_plan
        if (
            self.adaptive_draft is not None
            and context.recent_themes
            and plan.growth_adaptation_summary
        ):
            draft = self.adaptive_draft
        if self.align_to_plan:
            draft = _align_draft_to_plan(draft, context)
        return DailyWinGenerationResult(
            draft=draft,
            provider=self.provider,
            model=self.model,
            prompt_version=PROMPT_VERSION,
            provider_request_id="fake-request",
            input_tokens=11,
            output_tokens=22,
            total_tokens=33,
            latency_ms=5,
        )


def _align_draft_to_plan(
    draft: DailyWinDraft, context: DailyWinModelContext
) -> DailyWinDraft:
    plan = context.instruction_plan
    supporting = [
        code
        for code in (plan.supporting_skill_code, plan.growth_target_code)
        if code and code != plan.primary_skill_code
    ][:2]
    updates: dict[str, object] = {
        "primary_skill_code": plan.primary_skill_code,
        "supporting_skill_codes": supporting,
        "duration_minutes": plan.duration_minutes,
    }
    if plan.growth_adaptation_summary and draft.adaptation_summary is None:
        updates["adaptation_summary"] = plan.growth_adaptation_summary
    elif not context.recent_themes:
        updates["adaptation_summary"] = None
    probe = plan.assessment_probe if isinstance(plan.assessment_probe, dict) else {}
    task = str(probe.get("observable_task") or "")
    expected = str(probe.get("expected_outcome") or "")
    if task:
        updates["observation_focus"] = task
        learn = draft.segments[0]
        steps = list(learn.steps)
        if task not in steps:
            steps = [task, *steps][:6]
        learn = learn.model_copy(update={"steps": steps})
        checks = list(draft.success_checks)
        if expected and expected not in checks:
            checks = [expected, *checks][:4]
            updates["success_checks"] = checks
        updates["segments"] = [
            learn,
            draft.segments[1],
            draft.segments[2],
        ]
    aligned = draft.model_copy(update=updates)
    return _satisfy_renderer_contracts(aligned, plan)


def _satisfy_renderer_contracts(
    draft: DailyWinDraft, plan: InstructionPlanContext
) -> DailyWinDraft:
    learn, do, grow = draft.segments
    steps = list(learn.steps)
    if plan.scaffold_level == "three_step_visual":
        pads = (
            "Touch the example.",
            "Say the next move.",
            "Move to one independent try.",
        )
        while len(steps) < 3:
            steps.append(pads[len(steps)])
        steps = steps[:3]
    if plan.instruction_mode == "review" and len(steps) < 2:
        steps.append("Try one small variation, then pause.")
    learn = learn.model_copy(update={"steps": steps})
    do = do.model_copy(
        update={
            "title": do.title.replace("final", "next").replace("Final", "Next"),
            "steps": [
                step.replace("final challenge", "practice try")
                .replace("final mission", "practice try")
                .replace("final check", "practice try")
                .replace("final test", "practice try")
                for step in do.steps
            ],
        }
    )
    grow = grow.model_copy(
        update={
            "steps": [
                step.replace("final challenge", "practice try")
                .replace("final mission", "practice try")
                .replace("final check", "practice try")
                .replace("final test", "practice try")
                for step in grow.steps
            ]
        }
    )
    return draft.model_copy(update={"segments": [learn, do, grow]})
