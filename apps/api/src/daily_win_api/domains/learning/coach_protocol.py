"""Application-owned parent coaching protocol. The LLM does not invent this."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from daily_win_api.domains.learning.enums import InstructionMode, ScaffoldLevel

COACH_PROTOCOL_V1 = "coach_protocol_v1"

LEVEL_WAIT = "wait"
LEVEL_METACOGNITIVE = "metacognitive"
LEVEL_LIGHT_CUE = "light_cue"
LEVEL_STRATEGY = "strategy"
LEVEL_MODEL = "analogous_model"
LEVEL_REDUCE = "reduce_one_step"

LADDER = (
    LEVEL_WAIT,
    LEVEL_METACOGNITIVE,
    LEVEL_LIGHT_CUE,
    LEVEL_STRATEGY,
    LEVEL_MODEL,
    LEVEL_REDUCE,
)

_MODE_CEILING = {
    InstructionMode.DIAGNOSTIC: LEVEL_WAIT,
    InstructionMode.REVIEW: LEVEL_LIGHT_CUE,
    InstructionMode.PRACTICE: LEVEL_STRATEGY,
    InstructionMode.INTRODUCE: LEVEL_MODEL,
    InstructionMode.REMEDIATION: LEVEL_REDUCE,
}

_BANNED_PHRASES = (
    "you are so smart",
    "great job!",
    "good enough",
    "never help",
    "make them cry",
    "failure builds character",
)

GENERIC_COACH_PHRASES = (
    "provide appropriate support",
    "encourage productive struggle",
    "observe learner behavior",
)


@dataclass(frozen=True)
class CoachCue:
    label: str
    text: str


@dataclass(frozen=True)
class CoachProtocol:
    coach_goal: str
    expected_challenge_level: str
    initial_wait_behavior: str
    prompt_ceiling: str
    allowed_prompt_levels: tuple[str, ...]
    correction_policy: str
    struggle_policy: str
    success_response: str
    frustration_response: str
    self_correction_response: str
    independence_goal: str
    assessment_boundary: str
    things_to_avoid: tuple[str, ...]
    coach_card: tuple[str, ...]
    cues: tuple[CoachCue, ...]
    teach_the_coach: bool
    one_thing_to_improve: str | None
    wait_guidance: str | None
    why_this_coaching: str
    session_shape: tuple[str, ...]
    protocol_version: str = COACH_PROTOCOL_V1

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["cues"] = [{"label": cue.label, "text": cue.text} for cue in self.cues]
        payload["allowed_prompt_levels"] = list(self.allowed_prompt_levels)
        payload["things_to_avoid"] = list(self.things_to_avoid)
        payload["coach_card"] = list(self.coach_card)
        payload["session_shape"] = list(self.session_shape)
        return payload


def build_coach_protocol(
    *,
    instruction_mode: InstructionMode,
    scaffold: ScaffoldLevel,
    age_years: int,
    skill_code: str,
    academic_band: str | None,
    growth_target_code: str | None,
) -> CoachProtocol:
    ceiling = _MODE_CEILING[instruction_mode]
    allowed = LADDER[: LADDER.index(ceiling) + 1]
    older = age_years >= 8
    diagnostic = instruction_mode is InstructionMode.DIAGNOSTIC
    remediation = instruction_mode is InstructionMode.REMEDIATION
    review = instruction_mode is InstructionMode.REVIEW
    challenge = "productive"
    if academic_band == "retained" and review:
        challenge = "productive"
    if remediation or scaffold is ScaffoldLevel.HIGH:
        challenge = "supported_challenge"
    wait = (
        "Give them a moment to think before helping."
        if older
        else "Wait before helping. A short pause is enough."
    )
    boundary = (
        "Do not teach or hint before the check. Clarifying the task is allowed."
        if diagnostic
        else "Help is allowed after an independent attempt, using the prompt ladder."
    )
    if diagnostic:
        goal = "Collect a clean first signal. Do not teach the answer first."
        card = (
            "Let them try the check independently.",
            "If they are confused about the instructions, clarify only.",
            "We are finding the right level, not scoring them.",
        )
        cues = (
            CoachCue("WAIT", wait),
            CoachCue("WATCH FOR", "Can they attempt the check without teaching?"),
        )
        why = "Diagnostic mode forbids instructional prompting before the probe."
    elif remediation:
        goal = "Keep the objective, add support, and protect dignity."
        card = (
            "Start with a short independent try.",
            "If they are stuck, ask what they notice, then give a usable next step.",
            "Reduce one step if repeated help is still not enough.",
        )
        cues = (
            CoachCue("ASK", "What do you notice? What could you try first?"),
            CoachCue("HINT", "Point to the relevant part. Do not give the answer yet."),
            CoachCue("WATCH FOR", "Is the work still too hard even with support?"),
        )
        why = "Remediation allows a higher prompt ceiling, including reducing one step."
    elif review:
        goal = "Check whether a previously shown skill still holds independently."
        card = (
            "Expect more independence than a first-teach session.",
            "If they miss, wait, then ask a strategy question.",
            "Do not turn review into a lecture.",
        )
        cues = (
            CoachCue("WAIT", wait),
            CoachCue(
                "LET THEM FIX IT",
                "If they catch an error, do not correct the rest yet.",
            ),
        )
        why = "Review expects higher independence; modeling is not the first move."
    elif instruction_mode is InstructionMode.INTRODUCE:
        goal = "Introduce the skill with a model only after they attempt."
        card = (
            "Let them try first.",
            "If stuck, ask a plan question, then show a similar example.",
            "Keep the focus on today's one skill.",
        )
        cues = (
            CoachCue("WAIT", wait),
            CoachCue("ASK", "What's your plan?"),
            CoachCue(
                "HINT",
                "You may model a similar example, not the assessment item.",
            ),
        )
        why = "Introduce allows modeling a similar example after an attempt."
    else:
        goal = "Practice the skill with prompts before modeling."
        card = (
            "Let them attempt independently.",
            "If stuck, ask what they notice before giving a hint.",
            "We're watching whether they can use the strategy without help.",
        )
        cues = (
            CoachCue("WAIT", wait),
            CoachCue("ASK", "What could you try first?"),
            CoachCue("LET THEM FIX IT", "If they self-correct, do not take over."),
        )
        why = "Practice uses the prompt ladder; modeling is not the first support."
    avoid = (
        "Do not give the answer immediately.",
        "Do not praise intelligence.",
        "Do not shame errors.",
        "Do not correct every non-target mistake.",
        "Do not lecture.",
        "Do not turn this into a contest with other children.",
    )
    if diagnostic:
        avoid = avoid + ("Do not teach before the check.",)
    one_thing = None
    if skill_code.startswith("writing."):
        one_thing = (
            "Coach only today's writing target. Other errors can be noticed, "
            "not all corrected at once."
        )
    teach = (
        not diagnostic
        and older
        and instruction_mode in {InstructionMode.PRACTICE, InstructionMode.REVIEW}
    )
    success = (
        "Name the specific move: strategy, self-correction, or independent try."
    )
    frustration = (
        "Acknowledge, wait, then ask a strategy question. "
        "If they disengage, shorten and keep dignity. Do not push through distress."
    )
    struggle = (
        "Challenge should stay achievable with support. "
        "Repeated significant help means reduce complexity, not push harder."
    )
    return CoachProtocol(
        coach_goal=goal,
        expected_challenge_level=challenge,
        initial_wait_behavior=wait,
        prompt_ceiling=ceiling,
        allowed_prompt_levels=allowed,
        correction_policy=(
            "Wait for an attempt. Use the next allowed ladder step. "
            "Never jump from a wrong answer to explaining the solution."
        ),
        struggle_policy=struggle,
        success_response=success,
        frustration_response=frustration,
        self_correction_response=(
            "If they notice and fix it, pause. That is useful evidence, "
            "not the same as a first-attempt correct."
        ),
        independence_goal=(
            "More independent reasoning."
            if older
            else "A genuine attempt before adult rescue."
        ),
        assessment_boundary=boundary,
        things_to_avoid=avoid,
        coach_card=card[:3],
        cues=cues,
        teach_the_coach=teach,
        one_thing_to_improve=one_thing,
        wait_guidance=wait if not remediation else None,
        why_this_coaching=why,
        session_shape=(
            "launch",
            "core_challenge",
            "apply_or_explain",
            "growth",
            "reflection",
        ),
    )


def protocol_from_dict(payload: dict[str, object] | None) -> CoachProtocol | None:
    if not payload:
        return None
    cues_raw = payload.get("cues") or []
    cues = tuple(
        CoachCue(str(item.get("label") or ""), str(item.get("text") or ""))
        for item in cues_raw
        if isinstance(item, dict)
    )
    return CoachProtocol(
        coach_goal=str(payload.get("coach_goal") or ""),
        expected_challenge_level=str(payload.get("expected_challenge_level") or ""),
        initial_wait_behavior=str(payload.get("initial_wait_behavior") or ""),
        prompt_ceiling=str(payload.get("prompt_ceiling") or LEVEL_WAIT),
        allowed_prompt_levels=tuple(
            str(item) for item in (payload.get("allowed_prompt_levels") or ())
        ),
        correction_policy=str(payload.get("correction_policy") or ""),
        struggle_policy=str(payload.get("struggle_policy") or ""),
        success_response=str(payload.get("success_response") or ""),
        frustration_response=str(payload.get("frustration_response") or ""),
        self_correction_response=str(payload.get("self_correction_response") or ""),
        independence_goal=str(payload.get("independence_goal") or ""),
        assessment_boundary=str(payload.get("assessment_boundary") or ""),
        things_to_avoid=tuple(
            str(item) for item in (payload.get("things_to_avoid") or ())
        ),
        coach_card=tuple(str(item) for item in (payload.get("coach_card") or ())),
        cues=cues,
        teach_the_coach=bool(payload.get("teach_the_coach")),
        one_thing_to_improve=(
            str(payload["one_thing_to_improve"])
            if payload.get("one_thing_to_improve")
            else None
        ),
        wait_guidance=(
            str(payload["wait_guidance"]) if payload.get("wait_guidance") else None
        ),
        why_this_coaching=str(payload.get("why_this_coaching") or ""),
        session_shape=tuple(str(item) for item in (payload.get("session_shape") or ())),
        protocol_version=str(payload.get("protocol_version") or COACH_PROTOCOL_V1),
    )


def contains_banned_coaching(text: str) -> bool:
    lowered = text.lower()
    return any(item in lowered for item in _BANNED_PHRASES)


def contains_generic_coach_language(text: str) -> bool:
    lowered = text.lower()
    return any(item in lowered for item in GENERIC_COACH_PHRASES)
