# Daily Win

Daily Win is a parent-operated app that helps parents intentionally develop their children through short personalized activities. AI is a copilot for the parent: it proposes a Daily Win, the parent and child complete it together offline, and parent feedback updates what the system understands about the child so the next activity adapts.

It is not a child chatbot, an AI tutor that replaces the parent, or a product where the child is simply handed a tablet.

Initial focus: parents and guardians of elementary-age children (approximately ages 5–9).

See [docs/product.md](docs/product.md) for vision, loop, and non-goals, and [docs/architecture.md](docs/architecture.md) for invariants, memory, tenancy, and the ModelGateway boundary. Agent operating rules live in [AGENTS.md](AGENTS.md).

## Repository

```
daily-win/
  apps/
    mobile/    # Expo (React Native, TypeScript, Expo Router)
    api/       # FastAPI (Python 3.12, uv, SQLAlchemy, Alembic, Pydantic)
  docs/        # Product and architecture documentation
  infra/       # Local infrastructure (PostgreSQL via Docker Compose)
  scripts/     # Maintainer scripts
```

Application code is not scaffolded yet. Development is Windows + Cursor Agent + Git/GitHub. Runtime shape is a modular monolith with PostgreSQL.
