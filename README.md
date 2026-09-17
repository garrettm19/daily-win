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
  infra/       # Local infrastructure
  scripts/     # Maintainer scripts
  docker-compose.yml  # Local PostgreSQL
```

Development is Windows + Cursor Agent + Git/GitHub. Runtime shape is a modular monolith with PostgreSQL.

## Local development

Start PostgreSQL:

```powershell
docker compose up -d db
```

Run the API so a physical phone on the same Wi-Fi can reach it:

```powershell
uv --directory apps/api run uvicorn daily_win_api.main:app --reload --host 0.0.0.0 --port 8000
```

Copy `apps/api/.env.example` to `apps/api/.env` only if you need to override the local defaults.

Seed the synthetic demo household/child (safe to run more than once):

```powershell
uv --directory apps/api run python -m daily_win_api.dev
```

For Expo Go on a physical phone, copy `apps/mobile/.env.example` to `apps/mobile/.env.local` and set `EXPO_PUBLIC_API_URL` to this computer's LAN IPv4, for example `http://192.168.x.x:8000`. Do not commit `.env.local`. Restart Expo after changing it.

Run the mobile app:

```powershell
npm --prefix apps/mobile start
```
