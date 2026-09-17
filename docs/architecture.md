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
