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
Derived learner profile    (rebuildable projection of current understanding)
        ↓
Next Daily Win + briefing  (generated from derived state + recent evidence)
```

- **Canonical:** evidence and events in PostgreSQL (facts, measurements, parent observations, and separately labeled AI inferences).
- **Derived:** the current learner profile. It can be deleted and rebuilt from evidence. It is not the ledger.
- **Not memory:** chat transcripts, provider thread IDs, and prompt/response logs. Those may exist for debugging under strict redaction rules, but they do not constitute what the system “knows” about a child.

Inferences must store (or reference) the evidence IDs they were based on, plus enough model/prompt version metadata to reproduce or audit the decision later.

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
- `learning` — skill taxonomy, goals, evidence ledger, derived skill state
- `daily_wins` — generated activities and AI-run provenance

Current tables:

| Table | Role |
| --- | --- |
| `households` | Tenant |
| `children` | Learner belonging to a household |
| `child_baselines` | Appendable parent-reported snapshots |
| `skills` | Application-owned taxonomy (`code` is stable) |
| `child_goals` | Active skill priorities for a child |
| `learning_events` | Canonical append-only evidence ledger |
| `learner_skill_state` | Current derived state, rebuildable from events |
| `learner_skill_state_evidence` | Lineage from derived state to supporting events |
| `ai_runs` | Provider call provenance (no raw prompts or child narrative) |
| `daily_wins` | Immutable generated Daily Win artifacts |
| `daily_win_feedback` | Immutable parent reflection for one Daily Win |

`learning_events.evidence_kind` distinguishes **FACT**, **MEASUREMENT**, **OBSERVATION**, and **INFERENCE**. `source` records who reported it (for example PARENT, SYSTEM, ASSESSMENT, AI). Corrections use `supersedes_event_id` rather than mutating history. `learner_skill_state` is not the ledger and must not be treated as canonical memory.

Parent feedback is stored as `daily_win_feedback` and converted by application code into canonical `learning_events` (a completion observation plus a primary-skill observation). `learner_skill_state` is rebuilt by a deterministic projector (`trend_projector_v1` for persistence). Adaptation policy is application-owned (`AdaptationDirective`) and is supplied to generation through the Context Builder. The current generator prompt is `daily_win_generator_v3`; historical prompt versions remain frozen in source.

`learning_events` may carry nullable `daily_win_id` and `daily_win_feedback_id` for lineage. `daily_win_feedback` is owned by the same household, child, and Daily Win through a composite foreign key, and V0.1 allows one submission per Daily Win.

## Demo API (development only)

`GET /api/v1/demo/child-profile` returns the seeded synthetic child for local Expo development. It is registered only when `APP_ENV` is a development environment (`local`, `development`, `dev`, `test`). It is not tenant authorization and must not exist in production.

`POST /api/v1/demo/daily-wins/generate`, `GET /api/v1/demo/daily-wins/latest`, `POST /api/v1/demo/daily-wins/{daily_win_id}/feedback`, and `POST /api/v1/demo/reset` follow the same restriction. Generation goes through ModelGateway; the mobile app never holds a provider key. If the latest Daily Win has no reflection, generate refuses with `feedback_required`.

`POST /api/v1/demo/reset` restores the synthetic Hayes child to the seeded starting condition. It deletes demo-derived `daily_win_feedback`, `learner_skill_state_evidence`, `learner_skill_state`, `learning_events`, `daily_wins`, and `ai_runs` for that child only. It does not delete the demo household, Hayes, baseline, goals, or the skill taxonomy, and it does not touch other households. Local command: `uv --directory apps/api run python -m daily_win_api.dev.reset`.

## Daily Win generation

A Context Builder loads a bounded snapshot: nickname, latest parent-reported baseline, active goals, related `learner_skill_state` rows, at most 10 recent `learning_events`, at most 3 recent Daily Wins, and a structured `AdaptationDirective`. Event summaries sent to the model are concise parent observations, not raw database rows. Database IDs stay in an internal `ai_runs.context_manifest` and are not sent to the model.

`ModelGateway` is the only provider boundary. The OpenAI implementation uses the Responses API with Structured Outputs and `store=False`. Application code validates skill codes against the taxonomy, requires the primary skill to match the #1 active goal, and runs deterministic physical-safety checks before persisting a `daily_wins` row. Failed generations record a sanitized `ai_runs` status and do not persist a Daily Win.

## ModelGateway boundary

```
Expo app  --HTTP-->  FastAPI API  -->  ModelGateway  -->  model provider
                         |                    |
                    tenant auth,         keys, schemas,
                    safety, persistence  validation, versions
```

- The mobile app talks only to the Daily Win API. It must not include provider SDKs or API keys.
- The API performs tenancy authorization, safety checks, persistence, and schema validation.
- `ModelGateway` is the only module that speaks to an LLM/model provider. Application code asks it for typed results; it does not scatter provider calls across features.
- Provider replacement should require changing the gateway implementation, not rewriting product workflows.
- Prompts and model identifiers are versioned so generations remain auditable.

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
| Mobile | Expo, React Native, TypeScript, Expo Router, Node 24 LTS, npm |
| Backend | FastAPI, Python 3.12, uv, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL |
| Shape | Modular monolith |
