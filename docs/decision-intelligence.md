# Daily Win — Decision intelligence

Status: **optional, provider-neutral, not required for generation.**

Daily Win must not become a thin ChatGPT wrapper, and it also must not become a thin Jev wrapper. Typed decision models may **verify** fuzzy judgments. They may never own learner truth.

As of **September 2026**, TypeSafe’s Jev is **early access**. Do not architect Daily Win around its continued availability, pricing, latency, or calibration claims.

## The System One / Jev pattern

TypeSafe AI publicly describes a class of models it calls **System One** models. Jev is the first public model in that class.

Reported product shape (from vendor documentation and launch materials):

- Input: unstructured or structured **state**, plus a list of **typed questions**.
- Output: typed answers, not prose. Typical primitives:
  - **Noul** — yes/no with a probability in `[0, 1]`
  - **Choice** — one option from a closed set, plus a distribution
  - **Score** — position on an ordered scale
- Questions over the same state can be evaluated **in parallel**.
- The model does not generate free text, so there is no completion to parse and no output-side type error of the “wrong JSON shape” kind.

### Vendor claims (not independently established)

Treat the following as **VENDOR CLAIMS** unless Daily Win has labelled evals of its own:

- Similar intelligence to LLMs on System One-shaped tasks, with roughly two orders of magnitude better speed/efficiency.
- Typical latency on the order of ~70–500 ms (sometimes cited around 100 ms).
- Input pricing on the order of $0.042 per million tokens; output tokens free.
- “Can’t hallucinate” because it cannot emit unconstrained strings.
- Probabilities are calibrated / epistemically honest (TypeSafe also describes training with “Reinforcement Learning for Calibrated Decisions”).

Independent commentary already notes that some **confidence** fields may be **derived from the returned distribution** (for example a peakedness summary) rather than a proven probability of being correct. Daily Win must calibrate thresholds on **its own labelled data**.

Early access / waitlist status can change. Availability through third-party gateways can change. **Do not require TypeSafe credentials. Do not call Jev live in this repository.**

## How this differs from generative LLMs

| | Generative LLM (Terra via ModelGateway) | Typed decision model (DecisionGateway) |
| --- | --- | --- |
| Job | Create the parent-facing activity | Answer atomic yes/no (or closed-set) questions |
| Output | Structured `DailyWinDraft` prose | `AtomicDecision` values + confidence |
| Failure mode | Invented skill, unsafe activity, vague coaching | Miscalibrated probability, forced choice among incomplete options |
| Allowed to write learner state | Never | Never |
| Required for a Daily Win | Yes (renderer) | No |

Do not use a generative LLM as a hidden “is this a good Daily Win?” judge. Do not use a decision model to write the activity.

## Daily Win abstraction

```
DecisionGateway  (Protocol)
  evaluate_activity(plan, draft, recent_themes) -> VerificationResult
```

Implemented today:

- `FakeDecisionGateway` for tests and offline fixtures.
- Optional injection into `generate_demo_daily_win`. Default path is **None** (deterministic validation only).

Possible future methods (not required now): `classify_optional_note`, `evaluate_risk`, `route_renderer`.

Every result stores typed values and, where the provider supports it, probability/confidence. Persist as `decision_runs`:

- `provider`, `model`, `schema_version`
- `output` JSONB (atomic decisions)
- `confidence`
- `instruction_plan_id` / optional `daily_win_id`
- `created_at`

Outputs are **INFERENCE**, disposable, and recomputable. They must not be copied into `learning_events` as FACT or MEASUREMENT.

## First use case: activity verification (`activity_verification_v1`)

Minimal inputs: `InstructionPlan`, `DailyWinDraft`, recent theme titles if needed.

**Do not send child identity, household IDs, or full profile when they are unnecessary.** Verification can run on plan + draft + titles.

Atomic questions (code combines them; never ask “is this a good Daily Win?”):

- `follows_target_skill`
- `assessment_probe_measures_target`
- `difficulty_matches_plan`
- `scaffold_matches_plan`
- `substantially_repeats_recent_activity`
- `physical_risk_present` (safety-critical)
- `parent_instructions_are_actionable`

## Confidence / escalation policy

Implemented in application code (`ai/decision/policy.py`). Starting **uncalibrated** threshold: `HIGH_CONFIDENCE = 0.8`.

| Situation | Verdict |
| --- | --- |
| Safety-critical fail at high confidence | FAIL → reject / regenerate |
| Safety-critical below threshold | UNCERTAIN → treat as reject in V0.3 retry loop |
| High-confidence non-safety fail, or high-confidence repeat | FAIL |
| Any low-confidence non-pass | UNCERTAIN |
| All high-confidence acceptable | PASS |

Decision verification remains **experimental** and is **off in the normal demo**. `HIGH_CONFIDENCE = 0.8` is an uncalibrated starting value, not production truth. Do not enable a live DecisionGateway until labelled evals calibrate thresholds. FakeDecisionGateway paths run in tests only.

Safety false negatives are scored more severely than false positives in `eval/decision_fixtures.py`.

## Potential uses

- Post-render verification (implemented as optional).
- Routing “this plan is simple” vs “unusual” **after** evals justify it.
- Classifying whether an optional parent note is a measurement vs a narrative (still must not auto-write MEASUREMENT).
- Extra physical-risk screen that still cannot override the deterministic safety validator.

## Prohibited uses

DecisionGateway / Jev-like models may **never** directly write:

- canonical evidence
- academic mastery / bands
- growth state
- child profile
- parent goals
- prerequisite relationships
- standards mappings
- peer percentiles

They may never invent instructional objectives. They may never replace InstructionPlanner.

## Provider abstraction and fallback

```
Application
  → DecisionGateway protocol
      → FakeDecisionGateway (tests, default absence = skip)
      → future adapter (Jev, another System One model, or an LLM constrained to the same schema)
```

Fallback:

1. Deterministic skill-contract + safety + schema validation always run.
2. If no DecisionGateway is configured, generation continues.
3. If a future provider is down, skip optional verification rather than blocking the parent — unless a safety-critical policy says otherwise (not enabled).
4. Never add LangChain solely for this boundary. Never require TypeSafe libraries.

## Vendor / privacy

A live decision provider is an additional **subprocessor**.

Do not send real child data until:

- privacy policy reviewed
- retention understood
- contractual terms reviewed
- production approval exists

Prefer verification payloads that contain **no child identity**. Plan + draft + recent titles are enough for the first use case.

OpenAI `store=False` does not apply to a different vendor. Assume a new provider has its own retention until proven otherwise.

## Evaluation / calibration requirements

Offline labelled fixtures live in `eval/decision_fixtures.py`. Metrics prepared:

- classification accuracy
- false-safe rate
- false-reject rate
- safety false negatives (weighted as more severe)
- confidence calibration (placeholder until live labelled runs exist)
- latency / cost (placeholder; no live Jev)

Three eval surfaces must stay separate: learner model, instruction planner, renderer/verifier. See [model-evaluation.md](model-evaluation.md).
