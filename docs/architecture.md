# Daily Win — Architecture

Daily Win is a **modular monolith**: one backend, one mobile app, one PostgreSQL database. Keep the design small enough to ship the core loop, and strict enough that child memory, tenancy, and model access cannot drift.

## Architecture invariants

1. **PostgreSQL/database state is the child's memory.** LLM conversation history is not memory and must not be treated as a source of truth about the child.
2. **Historical evidence/events are canonical.** Current learner profiles are **derived state** and must be rebuildable from evidence.
3. Keep these concepts distinct in storage, APIs, and prompts:
   - **FACT** — durable, checkable information (e.g. age band, language spoken at home).
   - **MEASUREMENT** — quantitative or structured results from an activity or assessment.
   - **PARENT OBSERVATION** — what a caregiver reported seeing or experiencing.
   - **AI INFERENCE** — a model-produced interpretation, never stored as if it were a fact.
4. **AI inferences must be traceable** to the evidence that supports them.
5. **Ownership is Household → Household Members → Children.** Do not model a child as belonging directly to one user.
6. **Tenant authorization must happen before** child information is sent to an AI provider.
7. The **mobile app never calls an LLM provider directly** and never contains model-provider API keys.
8. All model-provider access goes through a backend **ModelGateway** abstraction.
9. AI output uses **defined structured schemas** and is **validated by application code** before it is trusted or persisted.
10. **Authorization, security, and physical-activity safety** are application responsibilities (policy, validation, filtering, refusals in code). They are not delegated to prompt instructions.
11. **Child narrative/profile content must not appear** in standard logs or analytics.
12. Preserve support for:
    - multiple caregivers
    - child/account deletion
    - auditability
    - prompt/model versioning
    - learner-state reconstruction
    - future provider replacement
13. **Do not introduce unnecessary infrastructure** such as Kubernetes, Kafka, Redis, vector databases, or microservices unless a demonstrated future requirement justifies them.

## Memory architecture

```
Parent feedback / baseline
        ↓
Canonical evidence events  (append-oriented, historical, source of truth)
        ↓
Derived learner state      (rebuildable academic bands + growth trends)
        ↓
InstructionPlan            (application-owned; reason codes; not LLM)
        ↓
Generated Daily Win        (LLM renders the experience from the plan)
```

- **Canonical:** evidence and events in PostgreSQL (facts, measurements, parent observations, and separately labeled AI inferences). InstructionPlans are canonical **decisions**, not evidence about the child.
- **Derived:** `learner_skill_state`. It can be deleted and rebuilt from evidence. It is not the ledger. Academic mastery bands and growth trends stay on separate projectors.
- **Generated:** Daily Win content JSONB. Never learner truth.
- **Optional inference:** `decision_runs` from DecisionGateway. Disposable. Never ability.
- **Not memory:** chat transcripts, provider thread IDs, and prompt/response logs.

**THE LLM CREATES THE EXPERIENCE. DAILY WIN DECIDES THE LEARNING.**

Inferences must store (or reference) the evidence IDs they were based on, plus enough model/prompt version metadata to reproduce or audit the decision later. Instructional “why” is stored as reason codes, not chain-of-thought.

See [learner-model.md](learner-model.md), [curriculum.md](curriculum.md), [instruction-policy.md](instruction-policy.md), [decision-intelligence.md](decision-intelligence.md), and [ai-architecture.md](ai-architecture.md).

## Tenancy model

```
Household
  └── Household Members  (caregivers / guardians; multiple allowed)
  └── Children           (learners; belong to the household, not to one user)
```

- Authorization is household-scoped. A member may act on children in that household only after tenancy checks succeed.
- Never send child information to a model provider until the caller is authorized for that household and child.
- Design for child deletion and account deletion: canonical records, derived profiles, and provider payloads must be removable without leaving child narrative in logs.
- Do not shortcut this model with `user_id` as the owner of a child.
- Users and household memberships are not modeled yet. The household is already the tenant boundary; authenticated members will attach later.
- Child-owned rows carry both `household_id` and `child_id`, with a **composite foreign key** `(child_id, household_id) → children(id, household_id)`. PostgreSQL therefore rejects a row whose child belongs to Household A while `household_id` claims Household B.
- Row-Level Security is not enabled yet. It will follow authenticated tenant context.

## Domain data model

Packages live under `apps/api/src/daily_win_api/domains/`:

- `households` — tenant
- `children` — learner identity and parent-reported baselines
- `learning` — curriculum graph, goals, evidence ledger, derived skill state, instruction plans
- `daily_wins` — generated activities and AI-run provenance

Current tables:

| Table | Role |
| --- | --- |
| `households` | Tenant |
| `children` | Learner belonging to a household |
| `child_baselines` | Appendable parent-reported snapshots |
| `skills` | Application-owned hierarchy (`code` is stable; domain → strand → skill) |
| `skill_prerequisites` | Canonical prerequisite edges |
| `skill_standard_refs` | Curated public-standard metadata (not skill identity) |
| `child_goals` | Active skill priorities for a child |
| `learning_events` | Canonical append-only evidence ledger |
| `learner_skill_state` | Current derived state, rebuildable from events |
| `learner_skill_state_evidence` | Lineage from derived state to supporting events |
| `instruction_plans` | Application-owned instructional decisions + reason codes |
| `ai_runs` | Provider call provenance (no raw prompts or child narrative) |
| `decision_runs` | Optional typed DecisionGateway inferences (not learner truth) |
| `daily_wins` | Immutable generated Daily Win artifacts |
| `daily_win_feedback` | Immutable parent reflection for one Daily Win |
| `demo_sessions` | Development-only hash → synthetic household mapping (not authentication) |

`learning_events.evidence_kind` distinguishes **FACT**, **MEASUREMENT**, **OBSERVATION**, and **INFERENCE**. `source` records who reported it (for example PARENT, SYSTEM, ASSESSMENT, AI). Corrections use `supersedes_event_id` rather than mutating history. `learner_skill_state` is not the ledger and must not be treated as canonical memory.

Parent feedback is stored as `daily_win_feedback` and converted by application code into canonical `learning_events` (a completion observation, a persistence observation, and an optional academic MEASUREMENT when `academic_result` is present). `learner_skill_state` is rebuilt by deterministic projectors (`trend_projector_v1` for persistence; `academic_projector_v1` for academic skills). `InstructionPlanner` (`instruction_policy_v2`) selects the next skill, scaffold, and assessment probe **before** generation. The current generator prompt is `daily_win_generator_v5`; historical prompt versions remain frozen in source. Optional `DecisionGateway` may verify the rendered draft; it is not required and is not a live Jev dependency.

`learning_events` may carry nullable `daily_win_id` and `daily_win_feedback_id` for lineage. `daily_win_feedback` is owned by the same household, child, and Daily Win through a composite foreign key, and V0.1 allows one submission per Daily Win.

## Demo API (development only)

Demo routes are registered only when `APP_ENV` is a development environment (`local`, `development`, `dev`, `test`). They are **not tenant authorization** and must not exist in production. Clients send `X-Demo-Session` (32+ characters). The API stores only a SHA-256 hash. Missing or short secrets are rejected. This is not authentication.

A demo session may be **new** (household exists, no child yet) or **ready** (synthetic child/profile exists). `GET /api/v1/demo/session` reports that status. `POST /api/v1/demo/setup/hayes` seeds the known Hayes profile. `POST /api/v1/demo/setup/profile` accepts a bounded synthetic payload (`extra="forbid"`). `PATCH /api/v1/demo/profile` inserts a new latest baseline and updates active goals.

`GET /api/v1/demo/child-profile`, generate/latest/feedback, `GET /api/v1/demo/progress`, `GET /api/v1/demo/daily-wins`, and `GET /api/v1/demo/daily-wins/{daily_win_id}` require a configured child. Foreign or unknown Daily Win IDs return the same 404. Generation goes through ModelGateway; the mobile app never holds a provider key.

`POST /api/v1/demo/reset` and `POST /api/v1/demo/reset/activity` clear that session's Daily Wins, feedback, events, learner state, lineage, and AI runs while keeping the synthetic child/profile. `POST /api/v1/demo/reset/session` also removes that session's child/profile and returns first-run. Neither endpoint touches other sessions. Local command `uv --directory apps/api run python -m daily_win_api.dev.reset` wipes HTTP demo sessions back to first-run and restores the legacy in-process Hayes row used by tests.

**Real child personal information must not be used in the public-tunnel demo.**

See [docs/security.md](security.md), [docs/data-lifecycle.md](data-lifecycle.md), [docs/model-evaluation.md](model-evaluation.md), and [docs/educational-quality.md](educational-quality.md).

## Daily Win generation

A Context Builder loads the latest baseline and goals, derived skill state, a bounded evidence window, and recent titles, then **InstructionPlanner produces an InstructionPlan**. The renderer (`daily_win_generator_v5`) receives nickname, parent-reported engagement context, that plan, at most 6 evidence summaries, at most 3 recent titles, and allowlists. Event summaries are application-written sentences, not raw database rows. Database IDs stay in an internal `ai_runs.context_manifest` and are not sent to the model.

`ModelGateway` is the generative-provider boundary. The OpenAI implementation uses the Responses API with Structured Outputs and `store=False`. Application code requires `primary_skill_code` to match the InstructionPlan, runs deterministic physical-safety checks, and may optionally call `DecisionGateway.evaluate_activity`. Generation retries are capped at 3. Failed generations record a sanitized `ai_runs` status and do not persist a Daily Win. `DecisionGateway` is not required and must never write canonical learner state.

## ModelGateway boundary

```
Expo app  --HTTP-->  FastAPI API  -->  ModelGateway  -->  model provider
                         |                    |
                    tenant auth,         keys, schemas,
                    safety, persistence  validation, versions
```

- The mobile app talks only to the Daily Win API. It must not include provider SDKs or API keys.
- The API performs tenancy authorization, safety checks, persistence, and schema validation.
- `ModelGateway` is the only module that speaks to a **generative** LLM provider. Application code asks it for typed results; it does not scatter provider calls across features.
- Optional typed judgments use `DecisionGateway` (Fake in tests; no live Jev). That path is not required for generation.
- Provider replacement should require changing the gateway implementation, not rewriting product workflows.
- Prompts, model identifiers, instruction-policy version, and projector versions are recorded so generations remain auditable.
- Model routing (`model_routing_v1`) currently always selects Terra. Do not auto-switch to Luna until evals justify it.

## Repository structure

```
daily-win/
  apps/
    mobile/     # Expo / React Native / TypeScript / Expo Router
    api/        # FastAPI / Python 3.12 / uv / SQLAlchemy / Alembic / Pydantic
  docs/         # Product and architecture documentation
  infra/        # Local infrastructure (PostgreSQL via Docker Compose)
  scripts/      # Maintainer scripts
```

Approved local data plane: **PostgreSQL via Docker Compose**. Do not add extra runtime infrastructure in v0 without a demonstrated need.

## Approved technology

| Layer | Choice |
| --- | --- |
| Development | Windows, Cursor Agent, Git/GitHub |
| Mobile | Expo SDK 57 development build (not App Store Expo Go), React Native, TypeScript, Expo Router, Node 24 LTS, npm |
| Backend | FastAPI, Python 3.12, uv, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL |
| Shape | Modular monolith |
