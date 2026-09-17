# Daily Win — Agent Instructions

This file is the permanent operating contract for humans and AI agents working in this repository. Do not contradict it in code, prompts, docs, or later rules.

## Product

Daily Win is a **parent-operated** application that helps parents intentionally develop their children through short personalized activities.

AI is a **copilot for the parent**.

It is **not**:

- an unrestricted chatbot for children
- an AI tutor that replaces the parent
- a product where the child is simply handed a tablet

**Target:** parents/guardians of elementary-age children, initially ages **5–9**.

**Original loop:** a parent gives AI information about their child; AI creates a short personalized Daily Win; parent and child complete it together; the parent reports what happened; that feedback changes what the system understands about the child; future Daily Wins adapt.

A Daily Win may combine academics, real-world activities, physical challenges, persistence, independence, problem solving, communication, and practical/life skills.

## Core product loop

Parent onboarding → child baseline and goals → personalized Daily Win → short parent coaching briefing → parent + child perform activity **offline** → parent submits feedback → feedback becomes structured evidence → learner state updates → next Daily Win adapts.

## V0.1 demo

Prove one thing exceptionally clearly: **parent feedback changes the system's understanding of the child and visibly affects the next Daily Win.**

## Architecture invariants

1. **PostgreSQL/database state is the child's memory.** LLM conversation history is not memory.
2. **Historical evidence/events are canonical.** Current learner profiles are derived state and must be rebuildable from evidence.
3. Keep these concepts distinct: **FACT**, **MEASUREMENT**, **PARENT OBSERVATION**, **AI INFERENCE**.
4. **AI inferences must be traceable** to their supporting evidence.
5. **Ownership is Household → Household Members → Children.** Do not model a child as belonging directly to one user.
6. **Tenant authorization must happen before** child information is sent to an AI provider.
7. The **mobile app never calls an LLM provider directly** and never contains model-provider API keys.
8. All model-provider access goes through a backend **ModelGateway** abstraction.
9. AI output uses **defined structured schemas** and is **validated by application code**.
10. **Authorization, security, and physical-activity safety** are application responsibilities, not prompt instructions.
11. **Child narrative/profile content must not appear** in standard logs or analytics.
12. Preserve support for: multiple caregivers, child/account deletion, auditability, prompt/model versioning, learner-state reconstruction, and future provider replacement.
13. **Do not introduce unnecessary infrastructure** (Kubernetes, Kafka, Redis, vector databases, microservices) unless a demonstrated future requirement justifies them.

## Approved technology

| Layer | Stack |
| --- | --- |
| Development | Windows, Cursor Agent, Git/GitHub |
| Mobile | Expo, React Native, TypeScript, Expo Router, Node 24 LTS, npm |
| Backend | FastAPI, Python 3.12, uv, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL (Docker Compose locally) |
| Architecture | Modular monolith |

## Repository layout

```
daily-win/
  apps/mobile/    # Expo app (not yet scaffolded)
  apps/api/       # FastAPI service (not yet scaffolded)
  docs/           # Product and architecture documentation
  infra/          # Local infrastructure (e.g. Docker Compose)
  scripts/        # Maintainer scripts
```

Do not flatten this layout or add extra top-level application packages without an explicit architecture change.

## Agent working rules

- Read `docs/product.md` and `docs/architecture.md` before implementing product or architecture changes.
- Do not scaffold, add dependencies, or build features unless the current task asks for them.
- Do not change the approved architecture or add disallowed infrastructure.
- Prefer small, reviewable changes that preserve the invariants above.
- Put durable project rules in this file and in version-controlled Cursor rules. Do not rely on chat history as source of truth.
