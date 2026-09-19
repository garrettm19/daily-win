# Daily Win — Learner-model audit (V0.3)

This audit describes **what the backend actually stores and decides today**, after the V0.3 learner engine. It is not a product pitch. Classifications use the V0.3 layers: PROFILE CONTEXT, GOALS, CANONICAL EVIDENCE, DERIVED LEARNER STATE, INSTRUCTION DECISION, GENERATED EXPERIENCE, OPTIONAL DECISION-MODEL OUTPUT.

**Core principle:** the LLM creates the experience; Daily Win decides the learning.

## Explicit answers

### What does Daily Win actually know about a child?

Application-owned knowledge is PostgreSQL state scoped to a household/child:

- Identity nickname (`children.nickname`).
- Latest parent-reported baseline snapshot (age band, grade, interests, strengths, difficulties, motivators, response to difficulty, preferred duration).
- Active parent-selected goals against the application taxonomy.
- Append-only `learning_events` (FACT / MEASUREMENT / OBSERVATION / INFERENCE).
- Derived `learner_skill_state` rebuilt from those events (`trend_projector_v1` for persistence; `academic_projector_v1` for academic skills that have structured assessments).
- Generated Daily Wins and their InstructionPlans (what was offered and why).
- Optional `decision_runs` (typed inferences, not learner truth).

LLM conversation history is not knowledge. Chat transcripts are not stored.

### What is merely parent-reported?

Almost everything the system currently uses about a real child is parent-reported:

- Entire baseline snapshot.
- Goal priorities.
- Reflection categories (difficulty, engagement, completion, setback response).
- Optional free-text `what_helped` / `additional_note` (canonical on feedback only; not treated as measurement).
- Optional `academic_result` plus counts. Even when stored as MEASUREMENT, the reporter is still the parent (`source=PARENT`). Daily Win does not yet have an independent assessor.

### What has been measured?

Only structured `academic_result` values written as `skill_assessment` events with `evidence_kind=MEASUREMENT`. The allowlist is:

- `correct_independently`
- `correct_after_light_prompt`
- `correct_after_significant_help`
- `incorrect`
- `not_attempted`

Optional `correct_count` / `attempted_count` may accompany countable probes. Free text is never converted into a measurement.

The V0.3.1 development demo submits structured `academic_result` on V4 probe-bearing Daily Wins. V1/V2/V3 Wins without a persisted academic probe do not collect or manufacture academic measurements.

### What has been inferred?

- Persistence trend (`latest_signal`, `direction`) from parent setback observations — derived, algorithm-versioned, not a diagnosis.
- Academic band (`not_observed` / `emerging` / `developing` / `demonstrated` / `retained`) from structured measurements — derived, not mastery percentage.
- InstructionPlan reason codes — application policy, not an LLM chain-of-thought.
- Optional DecisionGateway atomic judgments — INFERENCE, disposable, never canonical ability.

Generated Daily Win copy (`personalization_summary`, `adaptation_summary`) is generated experience, not an inference ledger.

### How does old evidence affect the next task?

1. Feedback writes canonical events (completion observation, persistence observation, optional academic MEASUREMENT).
2. `rebuild_child_learner_states` projects persistence always, and academic skills that have assessment events.
3. `InstructionPlanner` reads parent priorities, academic snapshots, growth signal, prerequisites, recency/review, and recent themes.
4. The planner selects primary skill, mode, scaffold, difficulty, and probe **before** the LLM runs.
5. Prompt v4 receives that plan plus bounded evidence summaries (cap 6) and recent titles (cap 3).

Old evidence therefore affects the **instructional objective**. It does not become an unbounded biography dumped into the prompt.

### What decisions currently belong to code?

- Tenancy / demo-session isolation before any provider call.
- Taxonomy, prerequisites, and standards mappings.
- Academic and growth projectors.
- InstructionPlanner (skill, mode, scaffold, difficulty, probe, duration clamp, theme-avoid list).
- Skill-contract validation (`primary_skill_code` must equal the plan).
- Physical-safety validation and optional moderation.
- Confidence/escalation policy over DecisionGateway outputs.
- Hard maximum of 3 generation attempts.
- Model routing policy (`model_routing_v1` currently always Terra).
- What is FACT vs MEASUREMENT vs OBSERVATION vs INFERENCE.

### What decisions currently belong to the LLM?

Creative rendering of one Daily Win from an authoritative InstructionPlan:

- framing, theme implementation, wording, playful mechanics, concise parent coaching
- LEARN / DO / GROW steps and materials chosen from allowlists

The LLM must not change target skill, difficulty, scaffold, assessment objective, success criteria, evidence requirement, or safety rules. Application code rejects a draft whose primary skill does not match the plan.

### Can the system measure academic development yet?

**Yes, in the live demo when a V4 academic probe exists.** The measurement contract and academic projector require structured `academic_result` on feedback. Without that field, academic skills stay `not_observed` and the planner uses parent priority plus missing-evidence / prerequisite rules. Progress now shows academic bands in parent language, separate from growth.

### Can it distinguish independent performance from prompted performance?

**Yes, when `academic_result` is submitted.** The five-way result is canonical MEASUREMENT. Persistence still uses a coarser parent-reported setback scale (`kept_going_independently` vs prompt vs significant help vs disengaged). Those are OBSERVATION, not academic measurement.

### Can it distinguish one-time performance from retained learning?

**Yes, in the academic projector.** One independent success is at most `developing`. `demonstrated` needs independent success in at least two distinct sessions. `retained` needs independent successes spaced at least 7 days apart. Later weak sessions after independent success set `needs_remediation` and can move the band backward to `developing`.

### Can it explain WHY today's task was selected?

**Yes, in application metadata.** Each generation persists `instruction_plans` with:

- `primary_skill_id`
- `instruction_mode`
- `scaffold_level`
- `reason_codes` (for example `parent_priority`, `insufficient_independent_evidence`, `prerequisite_evidence_missing`, `review_spacing`, `regression_review`, `age_grade_appropriate`)
- versioned plan JSONB (`instruction_policy_v2`; historical rows may still be `instruction_policy_v1`)

No chain-of-thought is stored.

---

## Inventory of data types

| Type | Layer | Canonical / derived / generated / transient | Source | Ownership | Versioning | Lineage | Mutability | Rebuildable | Retention purpose | Sent to OpenAI | Logged | Needed for future personalization |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `households` | tenancy | Canonical | Demo seed / session | Household | — | Tenant root | Mutable name | No (identity) | Tenant boundary | No | No | Yes (authorization) |
| `children` | PROFILE | Canonical identity | Parent/demo setup | Household | timestamps | `household_id` | Nickname mutable | No (identity) | Learner identity | Nickname only | No | Yes (address the child) |
| `child_baselines` | PROFILE | Canonical snapshot, parent-reported | Parent | Household/child | `schema_version` | `recorded_at` append | Old rows immutable; edits insert latest | Snapshots retained | Engagement + age/duration context | Yes: latest snapshot fields | No | Yes for engagement; **does not prove ability** |
| `child_goals` | GOALS | Canonical assignment | Parent | Household/child | `active`/`priority` | `skill_id` | Active flags change; history of assignments is current-row based | Assignments not rebuilt from evidence | Priority, not mastery | No (v4 sends plan, not the goal list) | No | Yes (planner input) |
| `skills` | product config | Canonical taxonomy | Application catalog `curriculum_v1` | Product | `taxonomy_version`, `active` | `parent_code`, strand | Catalog upsert on seed | Seeded | Instructional vocabulary | Skill **codes** in plan/allowlist | No | Yes |
| `skill_prerequisites` | product config | Canonical graph | Application `PREREQUISITE_EDGES` | Product | catalog | `skill_code` → `prerequisite_code` | Seed insert | Seeded | Planner unlocks | No | No | Yes |
| `skill_standard_refs` | metadata | Canonical mapping | Curated CCSS refs | Product | `source`+`version` | `skill_code` | Seed insert | Seeded | Criterion reference only | No | No | Optional reporting; **not skill identity** |
| `learning_events` | CANONICAL EVIDENCE | Canonical, append-oriented | Application conversion of feedback | Household/child | `schema_version` | `daily_win_id`, `daily_win_feedback_id`, `supersedes_event_id` | No in-place rewrite | Events are the ledger | Memory | Bounded **summaries** only (cap 6) | No | Yes |
| Event FACT | evidence | Canonical | Not used in V0.3 demo loop | Household/child | schema | — | Append | Yes | Checkable facts later | No currently | No | Later |
| Event MEASUREMENT | evidence | Canonical | Optional `academic_result` | Household/child | schema | win/feedback FKs | Append | Yes | Academic projector | Summary of result, not raw IDs | No | Yes |
| Event OBSERVATION | evidence | Canonical | Parent reflection | Household/child | schema | win/feedback FKs | Append | Yes | Growth projector + bounded context | Concise signal phrase | No | Yes |
| Event INFERENCE | evidence | Canonical labeled inference | Not written by DecisionGateway today | Household/child | schema + optional confidence | evidence IDs required by policy | Append | Yes | Audit of AI claims | Must not be treated as fact | No | Only if labeled |
| `learner_skill_state` | DERIVED | Derived cache | Projectors | Household/child | `algorithm_version` | `learner_skill_state_evidence` | Replaced on rebuild | **Yes** | Fast read | No in v4 (plan carries `academic_band`) | No | Yes (planner) |
| Persistence state JSON | DERIVED | Derived trend | `trend_projector_v1` | Household/child | algorithm | observation events | Replaced | Yes | Growth coaching | Indirectly via plan `growth_adaptation_summary` | No | Yes |
| Academic state JSON | DERIVED | Derived band | `academic_projector_v1` | Household/child | algorithm | assessment events | Replaced | Yes | Mastery-like conservatism **without %** | Indirectly via plan `academic_band` | No | Yes |
| `instruction_plans` | INSTRUCTION DECISION | Canonical decision record | `InstructionPlanner` | Household/child | `policy_version` | `primary_skill_id`, reason codes | Insert-only | Deterministic from inputs | Explain WHY | Plan fields (no UUIDs) | No | Yes |
| `daily_wins` | GENERATED EXPERIENCE | Canonical generated artifact | Validated LLM draft | Household/child | `content_schema_version` | `ai_run_id`, `instruction_plan_id` | Immutable after persist | Not rebuilt from evidence | What was offered | Titles only as `recent_themes` | No | Novelty / avoid repeats |
| `daily_win_feedback` | CANONICAL EVIDENCE source | Canonical parent report | Parent | Household/child | — | one per win | Immutable after submit | No | Source of events | Not raw | No | Structured fields yes; free text no by default |
| Feedback free text | PROFILE/notes | Canonical on feedback row | Parent | Household/child | 400 char cap | feedback id | Immutable | No | Parent notes | **No** | No | Later, gated |
| `ai_runs` | operational | Metadata | Generation | Household/child | prompt/schema versions | `context_manifest` IDs | Insert/complete | Operational | Cost/debug | No | Exception **type names** only | No (not learner truth) |
| `decision_runs` | OPTIONAL DECISION OUTPUT | Inference metadata | Optional DecisionGateway | Household/child | `schema_version` | plan id; daily_win_id reserved | Insert | Disposable/recomputable | Audit typed judgments | Verification uses plan+draft+themes, not child identity | No | Calibration later |
| `demo_sessions` | operational | Mapping | Client secret hash | Dev only | — | household/child | Mutable child link | No | Isolation, **not auth** | No | No | No |
| `DailyWinModelContext` | transient | Transient renderer input | Context builder | Process | `INPUT_SCHEMA_VERSION=3` | Manifest IDs stay internal | Not stored as conversation | Rebuildable | One generation | Yes | No | N/A |
| `DailyWinDraft` | generated | Generated then validated | ModelGateway | Process → `daily_wins.content` | output schema | ai_run | Rejected drafts dropped | No | Parent-facing activity | Not stored at provider (`store=False`) | No | No |
| AssessmentProbe | product config | Catalog contract | `assessment_probe_v2` | Product | catalog_version | target_skill_code | Catalog | Seeded in plan JSON | Parent-observable check | Yes, inside InstructionPlan | No | Yes |
| Prompt v1/v2/v3/v4 | product config | Immutable source files | Application | Product | `PROMPT_VERSION` | `ai_runs.prompt_version` | Frozen files | — | Auditability | System+user prompt | No | Historical readability |
| Model routing | policy | Application policy | `model_routing_v1` | Product | policy version | — | Code | — | Future Luna/Terra split | Model name on ai_runs | No | Eval-gated |

---

## Gap classification

### CRITICAL

1. **Parent-reported measurements are still the only academic instrument.** Structured results reduce free-text contamination, but they are not an independent assessment. Do not claim school-grade accuracy or mastery.
2. **No production authorization.** Demo-session isolation is not tenant auth. Real-child data remains forbidden on this surface.

### IMPORTANT

1. **Progress distinguishes academic vs growth, still cautiously.** Academic bands are parent-facing labels, not mastery percentages. Strand-level goals (for example `writing.organization`) are not the same row as skill-level academic state (`writing.sentences.complete_sentence`).
2. **Growth constructs besides persistence** (`independence`, `communication`, `problem_solving`, life skills) have taxonomy rows but no dedicated projectors or probes.
3. **DecisionGateway is optional and off by default.** FakeDecisionGateway exists for tests. No live Jev/TypeSafe adapter. Verification cannot yet catch probe-fidelity failures in production generation.
4. **Confidence thresholds are uncalibrated** (`HIGH_CONFIDENCE = 0.8`). They are a policy shape, not production truth.
5. **Prompt still sends strengths, difficulties, and response_to_difficulty.** Instructional personalization is supposed to live in the plan. Those baseline fields remain available to the renderer for wording; they should be re-justified with eval evidence.
6. **History is newest-N, not cursor-paginated.** Bounded (`limit` 10–20) and indexed, but multi-year UX needs keyset pagination.
7. **`decision_runs.daily_win_id` is reserved** and not filled at verification time because the Daily Win row does not exist yet. Lineage today is via `instruction_plan_id`.
8. **Standards mappings are coarse** (some CCSS codes reused across nearby skills). They are metadata only; do not treat them as precise alignment claims.
9. **Progress observation list is batched** (skills and win titles loaded in two queries, capped at 8). Fine at demo scale; keep batching if history grows.

### LATER

1. Live DecisionGateway provider after privacy/contract review.
2. Calibrate thresholds with labelled eval data.
3. Route simple plans to Luna only after recorded evals.
4. Independent (non-parent) academic probes.
5. Knowledge tracing / item response theory.
6. Norm-referenced percentiles (explicitly out of scope until validated assessments and an appropriate population exist).
7. Formal deletion scheduler, RLS, production auth.
8. Vector search, Redis, Kafka, Elasticsearch — not justified.
9. Open-ended agent loops — prohibited unless evals prove a bounded retry is insufficient (already capped at 3).
