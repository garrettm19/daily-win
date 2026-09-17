from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.ai.schemas import (
    Adaptations,
    DailyWinDraft,
    DailyWinGenerationResult,
    DailyWinModelContext,
    DailyWinSegment,
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
    ) -> None:
        self.draft = draft or valid_daily_win_draft()
        self.adaptive_draft = adaptive_draft
        self.error = error
        self.provider = provider
        self.model = model
        self.calls: list[DailyWinModelContext] = []

    def generate_daily_win(
        self, context: DailyWinModelContext
    ) -> DailyWinGenerationResult:
        self.calls.append(context)
        if self.error is not None:
            raise self.error
        draft = self.draft
        directive = context.adaptation_directive
        if (
            self.adaptive_draft is not None
            and context.recent_daily_wins
            and directive is not None
            and directive.latest_signal != "no_signal"
        ):
            draft = self.adaptive_draft
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
