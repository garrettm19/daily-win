# Daily Win — Data lifecycle

PostgreSQL is the child's memory. LLM conversation history is not memory and must not be introduced as a second ledger.

This audit describes **what the V1 development demo actually does today**, plus planned retention/deletion behavior for a later production system. Planned production behavior is not implemented.

## Classification

| Class | Meaning |
| --- | --- |
| **CANONICAL DATA** | Historical records that the system treats as source of truth. Rebuild derived state from these. |
| **DERIVED DATA** | Current understanding that must be rebuildable from canonical evidence. |
| **TRANSIENT AI CONTEXT** | Bounded snapshot assembled for one model call. Not a memory store. |
| **OPERATIONAL METADATA** | Provenance, versions, token counts, demo-session hashes. Not child narrative. |

## Storage design review

Expected conclusion, confirmed by current code:

- PostgreSQL remains canonical storage.
- `learning_events` remain append-oriented evidence.
- `learner_skill_state` remains derived and rebuildable.
- `instruction_plans` are application-owned decision records, not a second child biography.
- `decision_runs` are optional disposable inferences.
- Structured Daily Win JSONB is appropriate for versioned generated content.
- No vector database is needed.
- No raw AI conversation history should be introduced.
- No giant mutable learner-profile JSON blob.

### Duplicated / unnecessary narrative

Found and reduced:

- Parent free-text `what_helped` was copied from `daily_win_feedback` into a `learning_events` payload. Canonical free text now stays on `daily_win_feedback`. The observation event keeps structured signal + `daily_win_feedback_id` lineage.

Still present and accepted:

- `daily_wins.title` / `objective` / `duration_minutes` are also inside `content` JSONB. That is generated-artifact denormalization for listing vs full payload, not a second child biography.
- `personalization_summary` may restate parent-reported interests. That is generated copy, not a second baseline table.
- `ai_runs.context_manifest` stores UUIDs that also exist on domain rows. IDs only; no narrative.

Hayes seed currently stores the motivator phrase `doing activities with a caregiver`. That is synthetic parent-reported text, not an inferred relationship. Historical Daily Wins generated under an older phrase are not rewritten.

## Data categories

### Parent / account data (future)

| | |
| --- | --- |
| Source | Not collected in V1. No users, emails, passwords, or household memberships. |
| Stored | No |
| Where | — |
| Why | — |
| Sent to OpenAI | No |
| Logged | No |
| Derived / rebuildable | — |
| Planned retention | Production accounts will need authenticated identity, hashed credentials or IdP subject, and a deletion workflow. Not implemented. |
| Class | Future canonical |

### Child profile / baseline

| | |
| --- | --- |
| Source | Development seed (synthetic Hayes) or parent-operated synthetic onboarding. |
| Stored | Yes |
| Where | `children` (id, household_id, nickname); `child_baselines` (age_years, grade, interests, strengths, current_difficulties, motivators, response_to_difficulty, preferred_activity_minutes, schema_version). |
| Why | Parent-reported starting context. Baseline is a snapshot, labeled parent-reported, not an established fact. It personalizes engagement; it does not prove ability. Profile edits insert a new latest baseline; they do not mutate older snapshots or Daily Wins. |
| Sent to OpenAI | Yes, as `DailyWinModelContext.parent_reported_baseline` plus nickname. No child UUID, no household UUID. |
| Logged | No. Logs use exception type names only. |
| Derived / rebuildable | Canonical snapshot. Not derived. |
| Planned retention | Delete with child/household. Formal scheduler not implemented. |
| Class | CANONICAL DATA (PROFILE CONTEXT) |

### Goals

| | |
| --- | --- |
| Source | Seeded active `child_goals` pointing at application-owned `skills`. |
| Stored | Yes |
| Where | `child_goals` (priority, skill_id, active); `skills` is global taxonomy. |
| Why | North-star priorities for InstructionPlanner. Goals influence priority; they do not prove weakness or mastery. |
| Sent to OpenAI | No as a goal list in v4. The planner consumes them; the renderer receives the InstructionPlan. |
| Logged | No |
| Derived / rebuildable | Canonical assignment. Skill definitions are application-owned. |
| Planned retention | Delete child goals with the child. Taxonomy remains. |
| Class | CANONICAL DATA (GOALS); taxonomy is product config |

### Daily Wins

| | |
| --- | --- |
| Source | Validated model output after schema, allowlist, and safety checks. |
| Stored | Yes |
| Where | `daily_wins` (title, objective, duration, primary_skill_id, instruction_plan_id, status, content JSONB, content_schema_version). |
| Why | The activity the parent sees and later reflects on. Generated content, not a fact about the child. |
| Sent to OpenAI | Prior wins: at most 3 **titles** as `recent_themes`. Full JSONB is not re-sent. |
| Logged | No narrative. Failed generations log exception class names. |
| Derived / rebuildable | Generated artifact. Not rebuilt from evidence. Historical record of what was offered. |
| Planned retention | Delete with child; demo reset deletes that session's wins. |
| Class | GENERATED EXPERIENCE (canonical artifact row) |

### Parent feedback

| | |
| --- | --- |
| Source | Parent reflection form. |
| Stored | Yes |
| Where | `daily_win_feedback`: categorical difficulty/engagement/completion/setback_response; optional `academic_result` / counts; optional `what_helped` and `additional_note` (max 400 chars). |
| Why | Immutable parent report for one Daily Win. Source for evidence events. Free text is never converted into MEASUREMENT. |
| Sent to OpenAI | Not as raw form fields. Later generations receive concise event summaries and an InstructionPlan. |
| Logged | No |
| Derived / rebuildable | Canonical. |
| Planned retention | Delete with child / demo reset. |
| Class | CANONICAL DATA |

### Learning events

| | |
| --- | --- |
| Source | Application conversion of feedback (and later other reporters). |
| Stored | Yes, append-oriented |
| Where | `learning_events` with `evidence_kind`, `source`, `event_type`, structured payload, optional skill, lineage FKs. |
| Why | Canonical evidence ledger. |
| Sent to OpenAI | At most 6 recent **summaries** written by application code (for example “Structured measurement for math.addition.within_10: correct_independently.”). Not raw `additional_note`. Not database IDs. |
| Logged | No |
| Derived / rebuildable | Canonical. Corrections should supersede, not mutate, in later versions. |
| Planned retention | Delete with child. |
| Class | CANONICAL EVIDENCE |

### Learner state

| | |
| --- | --- |
| Source | Deterministic projectors (`trend_projector_v1`, `academic_projector_v1`) over events. |
| Stored | Yes, as a cache of current understanding |
| Where | `learner_skill_state` + `learner_skill_state_evidence`. |
| Why | Fast read of persistence trend and academic band for planner and UI. Must remain rebuildable. No fake percentage mastery. |
| Sent to OpenAI | Not as raw state rows in v4. Academic band and growth coaching ride on the InstructionPlan. |
| Logged | No |
| Derived / rebuildable | **Yes. Derived.** |
| Planned retention | Rebuild or delete with evidence. Demo reset deletes it. |
| Class | DERIVED LEARNER STATE |

### Instruction plans

| | |
| --- | --- |
| Source | `InstructionScheduler` (`instruction_scheduler_v1`), `InstructionPlanner` (`instruction_policy_v4`), and `PlacementPolicy` (`placement_policy_v1`). |
| Stored | Yes |
| Where | `instruction_plans`: household/child, `primary_skill_id`, mode, scaffold, `reason_codes`, versioned `plan` JSONB. |
| Why | Answer “why did Daily Win choose this?” without storing chain-of-thought. |
| Sent to OpenAI | Plan fields only (no row UUID). Authoritative for the renderer. |
| Logged | No |
| Derived / rebuildable | Deterministic from planner inputs; persisted as a decision record. |
| Planned retention | Delete with child / demo reset. |
| Class | INSTRUCTION DECISION |

### Decision runs

| | |
| --- | --- |
| Source | Optional `DecisionGateway` (Fake in tests; no live Jev). |
| Stored | Yes when verification is injected |
| Where | `decision_runs`: provider, model, schema version, output JSONB, confidence, plan FK. |
| Why | Audit typed inferences. Never learner truth. |
| Sent to OpenAI | No. Verification inputs are plan + draft + recent titles. |
| Logged | No |
| Derived / rebuildable | Disposable / recomputable INFERENCE. |
| Planned retention | Operational; delete with child. Do not send real child data to a new vendor without privacy review. |
| Class | OPTIONAL DECISION-MODEL OUTPUT |

### AI context

| | |
| --- | --- |
| Source | Context Builder at generation time. |
| Stored | Not as a conversation. Manifest IDs stored on `ai_runs`. |
| Where | Process memory for the call; `ai_runs.context_manifest` for IDs/versions. |
| Why | One bounded generation. |
| Sent to OpenAI | The `DailyWinModelContext` JSON plus system/user prompt text. See [Exact payload sent to OpenAI](#exact-payload-sent-to-openai). |
| Logged | No. Prompt and response bodies are not written to logs or `ai_runs`. |
| Derived / rebuildable | Transient. Can be rebuilt from PostgreSQL if needed. |
| Planned retention | Do not start storing raw transcripts. |
| Class | TRANSIENT AI CONTEXT |

### AI outputs

| | |
| --- | --- |
| Source | ModelGateway structured `DailyWinDraft`. |
| Stored | Only after validation, as `daily_wins.content`. Rejected output is dropped. |
| Where | `daily_wins.content` JSONB. |
| Why | Display to the parent. |
| Sent to OpenAI | Not stored as a provider thread. `store=False`. |
| Logged | No raw output. |
| Derived / rebuildable | Generated artifact. |
| Planned retention | Same as Daily Wins. |
| Class | CANONICAL DATA (generated artifact) |

### `ai_runs` metadata

| | |
| --- | --- |
| Source | Generation attempt. |
| Stored | Yes |
| Where | `ai_runs`: household/child IDs, operation, provider, model, prompt/schema versions, status, context_manifest (IDs plus development latency/trigger/fingerprint fields; not prompt text), provider_request_id, token counts, latency, sanitized error_code, timestamps. |
| Why | Provenance and cost/debug without storing child narrative or completions. |
| Sent to OpenAI | No |
| Logged | Exception class on failure; not the manifest. |
| Derived / rebuildable | Operational. |
| Planned retention | Operational retention separate from learner evidence. Not scheduled yet. |
| Class | OPERATIONAL METADATA |

### Logs

| | |
| --- | --- |
| Source | Application logging. |
| Stored | Local process logs only in V1. No centralized audit sink. |
| Where | std logging. Messages use exception **type names**, not child profile text. |
| Why | Operator debugging. |
| Sent to OpenAI | No |
| Logged | Yes (this category). |
| Derived / rebuildable | — |
| Planned retention | Production needs PII-redacted, centralized logs and a retention policy. Not implemented. |
| Class | OPERATIONAL METADATA |

### Demo-session identifiers

| | |
| --- | --- |
| Source | Mobile generates a high-entropy secret once per installation (`X-Demo-Session`). |
| Stored | **Hash only** (`demo_sessions.session_hash` = SHA-256 hex). Raw secret is not stored on the server. Mobile persists the secret locally. |
| Where | `demo_sessions` maps hash → household_id + optional child_id + profile_source (`hayes`/`custom`). A session may exist before child setup (`child_id` null). Tester fingerprint is the first 6 hex chars of the hash, shown in development UI only. |
| Why | Isolate Mason and Cory on the shared development API. **Not authentication.** |
| Sent to OpenAI | No |
| Logged | No |
| Derived / rebuildable | Operational mapping. |
| Planned retention | Development-only. Production must not register this mechanism. |
| Class | OPERATIONAL METADATA |

## Exact payload sent to OpenAI

Each generation sends:

1. System prompt (`daily_win_generator_v5`).
2. User prompt wrapping `DailyWinModelContext` JSON:
   - `nickname`
   - parent-reported baseline: age, grade, interests, strengths, difficulties, motivators, response_to_difficulty, preferred minutes, `reporting_kind`
   - authoritative `instruction_plan` (skill, reasons, mode, difficulty, scaffold, probe, growth overlay, duration, theme constraints)
   - up to 6 bounded evidence summaries (`skill_code`, `summary`, `reporting_kind`)
   - up to 3 `recent_themes`
   - `allowed_skill_codes` (plan-derived)
   - `allowed_materials`

See [ai-architecture.md](ai-architecture.md) for why each field is present.

## Intentionally not sent or not stored

**Not sent to OpenAI:** child UUID, household UUID, baseline/goal/event/win UUIDs, demo session IDs, raw `additional_note`, raw `what_helped`, full prior Daily Win JSONB, prompts from earlier turns, API keys, tester session secrets, peer percentiles.

**Not stored:** raw prompts, raw model completions, provider conversation threads, vector embeddings of child narrative, mobile copies of the OpenAI key.

**Not claimed:** Zero Data Retention at the provider. See `docs/security.md`.

## V0.2 synthetic collection set (demo implementation)

The public-tunnel development build remains **synthetic-only**. Testers see: **Demo mode — use made-up information only.** Do not enter actual child personal information.

Onboarding/profile write accepts only:

- `nickname` (1–30 chars, fictional)
- `age_years` (integer 5–9; no date_of_birth)
- `grade` (`K`, `1`, `2`, `3`, `4`)
- `interests` (up to 5 short labels)
- `strengths` (up to 5)
- `current_difficulties` (up to 5, parent-reported)
- `response_to_difficulty` (allowlisted parent-reported phrase)
- `goal_codes` (2–3 codes from the onboarding catalog)
- `primary_goal_code` (must be one of `goal_codes`)
- `motivators` (up to 4)
- `preferred_activity_minutes` (10, 15, 20, or 25)

Unexpected fields are rejected (`extra="forbid"`), including `date_of_birth`, `last_name`, `email`, `address`, `school_name`, `medical_condition`, `diagnosis`, and `photo_url`.

The API does not collect full/legal name, exact date of birth, email, phone, home address, school name, teacher, precise location, medical/disability diagnosis, photos, audio, handwriting, or biometric information.

This is the **demo implementation**. Production onboarding for real children is not implemented and must not use this unauthenticated demo-session surface.
