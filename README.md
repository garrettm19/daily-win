# Daily Win

[![CI](https://github.com/garrettm19/daily-win/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/garrettm19/daily-win/actions/workflows/ci.yml)

Daily Win is a parent-operated app that helps parents intentionally develop their children through short personalized activities. AI is a copilot for the parent: it proposes a Daily Win, the parent and child complete it together offline, and parent feedback updates what the system understands about the child so the next activity adapts.

It is not a child chatbot, an AI tutor that replaces the parent, or a product where the child is simply handed a tablet.

Initial focus: parents and guardians of elementary-age children (approximately ages 5–9).

See [docs/product.md](docs/product.md) for vision, loop, and non-goals, and [docs/architecture.md](docs/architecture.md) for invariants, memory, tenancy, and the ModelGateway boundary. Security and data-handling notes live in [docs/security.md](docs/security.md) and [docs/data-lifecycle.md](docs/data-lifecycle.md). Model-evaluation rules live in [docs/model-evaluation.md](docs/model-evaluation.md). Agent operating rules live in [AGENTS.md](AGENTS.md).

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

Copy `apps/api/.env.example` to `apps/api/.env` only if you need to override the local defaults. Set `OPENAI_API_KEY` there for real Daily Win generation. The mobile app never receives this key.

Seed the synthetic demo household/child (safe to run more than once):

```powershell
uv --directory apps/api run python -m daily_win_api.dev
```

Reset **this installation's** demo activity history (Daily Wins, reflections, evidence, learner state) while keeping the synthetic profile. `POST /api/v1/demo/reset/session` returns that tester to first-run. Other testers' sessions are not affected. The CLI below wipes every HTTP demo session back to first-run and restores the legacy in-process Hayes row:

```powershell
uv --directory apps/api run python -m daily_win_api.dev.reset
```

The same per-session tools are available from the Expo app under **Demo controls** (development builds only): **Reset activity history** and **Restart demo from beginning**. A short tester fingerprint (for example `Tester: A31F92`) confirms two phones are not sharing a session. Demo routes are not registered in production. This is not authentication.

**REAL CHILD PERSONAL INFORMATION MUST NOT BE USED IN THE CURRENT PUBLIC-TUNNEL DEMO ENVIRONMENT.** Synthetic/demo data only.

Default model is `gpt-5.6-terra`. Do not run a large live model evaluation unless you intend to spend API budget. Small fake sample:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --sample 2
```

Copy `apps/mobile/.env.example` to `apps/mobile/.env.local` and set `EXPO_PUBLIC_API_URL` to the API the phone can reach (LAN IPv4 such as `http://192.168.x.x:8000`, or the current development tunnel). Do not commit `.env.local`. Restart Metro after changing it.

Physical iOS development uses an Expo SDK 57 **development build**, not App Store Expo Go. Windows cannot compile iOS locally; Mason needs an Expo account, EAS CLI, Apple Developer Program membership, the iPhone registered on the team, and iOS Developer Mode. From `apps/mobile`:

```powershell
npx eas-cli login
npx eas-cli init
npx eas-cli build --platform ios --profile development
npx expo start --dev-client
```

See [apps/mobile/README.md](apps/mobile/README.md) for the full device-install flow. Do not use Expo Go. App Store / TestFlight submission is not configured.

Run Metro for an already-installed development client:

```powershell
npm --prefix apps/mobile start
```
