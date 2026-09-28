# Coach Protocol (`coach_protocol_v1`)

The LLM does not invent the parent coaching philosophy. `CoachProtocol` is application-owned and stored on the InstructionPlan JSON for new (`instruction_policy_v4`) Wins. Historical plans do not receive a fake protocol retroactively.

## Inputs

Instruction mode, scaffold, learner band, growth target, age, skill.

## Fields

- coach_goal
- expected_challenge_level (`productive` or `supported_challenge`)
- initial_wait_behavior
- prompt_ceiling / allowed_prompt_levels
- correction_policy, struggle_policy
- success_response, frustration_response, self_correction_response
- independence_goal, assessment_boundary
- things_to_avoid
- coach_card (max 3 bullets: "Your job today")
- sparse during-activity cues (WAIT / ASK / HINT / WATCH FOR / LET THEM FIX IT)
- teach_the_coach (practice/review, age ≥ 8)
- one_thing_to_improve (writing)
- protocol_version

## Prompt ladder

| Level | Name | Use |
| --- | --- | --- |
| 0 | wait | Give the child time to think |
| 1 | metacognitive | "What do you notice?" / "What's your plan?" |
| 2 | light_cue | Point attention without the answer |
| 3 | strategy | Remind a previously learned strategy |
| 4 | analogous_model | Similar example, not the assessment item |
| 5 | reduce_one_step | Reduce complexity, keep the skill |

Never jump from a wrong answer to explaining the solution.

Mode ceilings:

- **Diagnostic:** wait only. Clarify instructions; do not teach before the probe.
- **Review:** through light_cue. Higher independence expected.
- **Practice:** through strategy. Prompt before modeling.
- **Introduce:** through analogous_model after an attempt.
- **Remediation:** through reduce_one_step.

Wait guidance is behavioral ("Give them a moment"), not a countdown.

## High standards + high support

Standards: attempt first; think before the answer; mistakes do not end the activity; do not call work "good enough" to avoid discomfort; increase challenge when evidence says too easy; belief in capability; improvement matters.

Support: calibrated challenge; no shame; mistakes as information; a usable next step; help when genuinely stuck; reduce one level without abandoning the objective; acknowledge frustration without immediate rescue; respect.

Support is not empty praise. Prefer process-specific feedback. Banned: "Great job!", "You are so smart!", "never help", "make them cry".

## Productive struggle

Desired: challenging but achievable with appropriate support. Do not glorify distress. Repeated significant support → reduce instructional complexity. The parent should not simply push harder.

Frustration:

- Mild + still engaged: acknowledge, wait, strategy question, continue
- Repeated failure: scaffold, reduce one step
- Disengagement: shorten/reset, preserve dignity, collect evidence, let tomorrow adapt

Stopping one activity is not a character failure.

## Observations (not first-attempt correctness)

Self-correction: `self_corrected` / `corrected_after_prompt` / `did_not_correct`. Useful for monitoring and independence; does not rewrite history as correct on first attempt.

Strategy chips are parent observations (math / reading / writing sets).

`performance_effort`: automatic / effortful_but_independent / effortful_with_support / not_observed. Supporting evidence only — not a cognitive score.

## Teach the Coach

Allowed mechanic when suitable (not every Win): the child explains how they solved it. Evidence about explanation/metacognition.

## Safety

No humiliation, punishment for mistakes, withholding affection, exercise as consequence, dangerous physical challenges, ignoring distress, forcing through pain, or negative labels. Physical bonus challenges stay optional, safe, and age-appropriate.
