"""Universal support semantics. Shared by probes, Progress, and eval."""

INDEPENDENT = (
    "The child completes the measured part without instructional help. "
    "A brief wait or encouraging presence is not a prompt."
)
LIGHT_PROMPT = (
    "One short cue or question that does not contain the answer. "
    "Example: 'What happened first?' or 'Try counting from one again.'"
)
SIGNIFICANT_HELP = (
    "Multiple prompts, modelling, a partial answer, rearranging for the child, "
    "direct guidance, or step-by-step support."
)
NOT_ATTEMPTED = "The measured part was skipped or not reached."
INCORRECT = (
    "The child attempted the measured part and the observable outcome was not met, "
    "even after any help that was given."
)

PARENT_ALLOWED_SUPPORT = (
    "After one independent try, you may give one short cue that does not "
    "contain the answer. More than that is significant help."
)

SUPPORT_LEVELS = {
    "correct_independently": INDEPENDENT,
    "correct_after_light_prompt": LIGHT_PROMPT,
    "correct_after_significant_help": SIGNIFICANT_HELP,
    "incorrect": INCORRECT,
    "not_attempted": NOT_ATTEMPTED,
}

REFLECTION_CAPTION = (
    "Independent: no instructional help on this part. "
    "Light prompt: one short cue that does not give the answer. "
    "A lot of help: multiple prompts, modelling, or a partial answer."
)
