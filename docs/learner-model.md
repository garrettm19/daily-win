# Daily Win — Learner model

Daily Win’s memory is PostgreSQL. The LLM does not remember the child.

```
canonical evidence
        ↓
deterministic learner model
        ↓
deterministic InstructionPlanner
        ↓
optional typed DecisionGateway verification (post-render)
        ↓
structured InstructionPlan
        ↓
generative activity renderer (prompt v4)
        ↓
deterministic validation (+ optional probabilistic verification)
        ↓
parent activity (offline)
        ↓
structured measurement / observation
        ↓
canonical evidence
```

**THE LLM CREATES THE EXPERIENCE. DAILY WIN DECIDES THE LEARNING.**

## Conceptual layers

Keep these distinct in storage, APIs, prompts, and parent copy.

### A. Profile context (parent-reported)

Latest `child_baselines` snapshot: nickname, age, grade, interests, strengths, difficulties, motivators, preferred duration, response to difficulty.

Profile information **personalizes engagement**. It does **not** prove ability.

### B. Goals

`child_goals` are parent priorities against the application taxonomy. They influence planner priority. They do **not** prove weakness or mastery.

### C. Canonical evidence

`learning_events` are append-oriented. Corrections use `supersedes_event_id`.

| `evidence_kind` | Meaning |
| --- | --- |
| FACT | Durable, checkable information |
| MEASUREMENT | Structured academic result (`academic_result`, optional counts) |
| OBSERVATION | What a caregiver reported seeing |
| INFERENCE | Model-produced interpretation, never stored as ability |

Do not turn arbitrary parent free text into MEASUREMENT.

### D. Derived learner state

`learner_skill_state` is a rebuildable cache.

- Academic skills (`state_mode=mastery`): `academic_projector_v1` → bands `not_observed`, `emerging`, `developing`, `demonstrated`, `retained`. No fake percentages.
- Growth/life (`state_mode=trend`): `trend_projector_v1` for persistence. Conservative direction over a short window. Do not reuse trend semantics for academic mastery.

`learner_skill_state_evidence` stores exact supporting event IDs.

### E. Instruction decision

`InstructionScheduler` (`instruction_scheduler_v1`) chooses today's academic goal. `InstructionPlanner` (`instruction_policy_v4`) produces an `InstructionPlan` **before** generation. `PlacementPolicy` (`placement_policy_v1`) chooses the diagnostic entry when evidence is sparse. Persisted as `instruction_plans` with reason codes. The LLM must not select the fundamental instructional objective.

### F. Generated experience

Validated `DailyWinDraft` stored on `daily_wins.content`. Never learner truth.

### G. Optional decision-model output

`decision_runs` from `DecisionGateway`. Typed inferences with provider/model/schema/confidence. Disposable. Must never write evidence, mastery, profile, goals, prerequisites, standards, or percentiles.

## Academic projector (`academic_projector_v1`)

Inputs: `skill_assessment` events with a known `AcademicResult`.

Rules (conservative):

- Unused / `not_attempted` evidence is skipped.
- Significant help or incorrect only → `emerging`.
- Any independent or lightly prompted success, without two independent sessions → `developing`.
- Independent success in **two distinct sessions** → `demonstrated`. Still not retained.
- Independent successes **≥ 7 days apart** → `retained`.
- After at least one independent session, if the **two most recent sessions** are all weak (incorrect / significant help / skipped) → band moves to `developing` and `needs_remediation=true`.
- One success never implies mastery. There is no percentage field.

Derived fields used by review scheduling:

- `last_practiced_at`
- `last_independent_success_at`
- `usable_evidence_count`
- `distinct_session_count`

`due_for_review`: demonstrated or retained skills with last practice ≥ 14 days ago.

## Growth projector (`trend_projector_v1`)

Persistence only in V0.3. Maps parent `setback_response` to signals. Direction requires a minimum usable window (`MIN_OBSERVATIONS_FOR_DIRECTION`). Copy stays observational (“returned after one prompt”), never trait language.

## Peer comparison

Daily Win is criterion-referenced (which skill/standard is in play) and within-child longitudinal (how support and correctness change over time).

There is **no percentile path**. LLM and DecisionGateway must never fabricate peer standing.

Daily Win history alone is not enough to rank a child against peers. A later percentile feature would need validated benchmark items, standard administration, a representative norm population, age/grade norms, psychometric calibration, and confidence/error estimates. Until then, Progress stays within-child. See [educational-quality.md](educational-quality.md).

## Rebuild

`rebuild_child_learner_states(session, household_id, child_id)`:

1. Rebuild persistence from skill observations.
2. Rebuild academic state only for academic skills that already have assessment events.

Deleting derived rows and rerunning the projector must recover the same bands and lineage for the same evidence.

## What the renderer is allowed to see

See [ai-architecture.md](ai-architecture.md) and the prompt-context minimization table there. Instructional personalization always wins over engagement personalization.
