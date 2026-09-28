# Learning engine observability

Development-only inspectability for Daily Win’s instructional loop. Not a parent product surface. Not learner truth.

## Runtime chain

```
PROFILE
    ↓
PLACEMENT (placement_policy_v1)
    ↓
CURRICULUM / PRIOR EVIDENCE (curriculum_v2)
    ↓
LEARNER STATE (derived; academic_projector_v1 / trend_projector_v1)
    ↓
INSTRUCTION SCHEDULER (instruction_scheduler_v1)
    ↓
INSTRUCTION PLANNER (instruction_policy_v4)
    ↓
INSTRUCTION PLAN
    ↓
RENDERER (prompt v5, gpt-5.6-terra)
    ↓
VALIDATOR (schema, renderer contracts, safety_rules_v1)
    ↓
DAILY WIN
    ↓
REFLECTION
    ↓
CANONICAL EVIDENCE (learning_events)
    ↓
PROJECTOR
    ↓
UPDATED LEARNER STATE
    ↓
NEXT PLAN
```

PostgreSQL events are memory. LLM history is not.

## Learning Trace

Backend-authoritative DTO from `GET /api/v1/demo/observatory/learning-trace`.

The mobile client must not reconstruct this logic.

Sections:

1. **Profile context** — synthetic nickname, age, grade, goals, interests, duration
2. **Scheduler** — selected academic goal, reason codes, urgency, deferred goals, starvation flag
3. **Placement** — policy version, strand, expected entry skill, sparse flag, reason codes
4. **Relevant prior evidence** — only skills on the current chain, not full history
5. **Curriculum decision** — target, parent-friendly name, prerequisite chain/status, standard ref
6. **Instruction plan** — skill, mode, difficulty, scaffold, overlay, reasons, policy
7. **Assessment plan** — probe, outcome, success criterion, counts, fresh-item, kind
8. **Renderer** — prompt/model/schema, required contracts, attempts, validation, safety
9. **Reflection** — academic result, counts, persistence, difficulty, engagement, completion
10. **State update** — BEFORE → EVIDENCE → AFTER for affected skills
11. **Next-Win implication** — deterministic application sentence
12. **Why not** — next skill, previous skill, second goal, review, terminal skill
13. **Next Win preparation** — not_started / generating / ready / failed / invalidated, trigger, fingerprint validity. No secrets.

Learning QA also shows **Generation performance** (latest and recent-5 totals vs provider ms) so a tester can see whether wait time is OpenAI or the backend.


Never included: DB UUIDs, session secret, OpenAI keys, raw system prompt, chain-of-thought, private notes, full historical JSON.

## Generation failure codes

| Trace code | Meaning |
| --- | --- |
| `configuration_error` | Provider is not configured |
| `provider_error` | Provider call failed |
| `schema_error` | Structured output failed (API still uses `schema_validation_failed`) |
| `unsafe_content` | Application safety rule rejected the draft (`safety_rule` only) |
| `renderer_contract_failed` | Includes failed contract IDs |
| `duplicate_generation` | Unreflected Win blocked another generate (`feedback_required`) |
| `instruction_plan_mismatch` | Draft did not follow the plan |

Failed `AiRun` rows persist for debugging. `InstructionPlan` rows are written only after a successful Daily Win, so a provider failure cannot leave half-created learner truth.

## Other development endpoints

| Path | Purpose |
| --- | --- |
| `/observatory/learning-qa` | One-screen bundle |
| `/observatory/learner-snapshot` | Parent-shaped derived state |
| `/observatory/curriculum-graph` | Strand position / blocked / retained |
| `/observatory/next-win-preview` | Runs the planner; does not create a Win |
| `/observatory/engine-versions` | Policy/prompt/model inventory |
| `/observatory/renderer-context` | Redacted bounded context + token estimate |

Device entry: **Learning QA** in Development controls (`apps/mobile/src/app/learning-qa.tsx`). Production builds must not expose it.

## Context budget

Renderer context is capped: 10 recent events, 6 evidence summaries, 3 recent Wins. It must not grow linearly with six months of history. Token estimates use characters/4 (no live tokenizer).

## User-facing claims

Progress, Insight, What changed today, and History copy is scanned for unsupported claims (`advanced`, `mastered`, `learns best`, `visual learner`, …). Claims must come from canonical evidence or deterministic derived state.
