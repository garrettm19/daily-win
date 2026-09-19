# Daily Win — Security

This document describes **controls that currently exist in the V1 development demo** separately from **controls required before production**. V1 is a development demo. It is **not** enterprise secure, not SOC 2 ready, and not approved for real-child production data.

## Development rule

**REAL CHILD PERSONAL INFORMATION MUST NOT BE USED IN THE CURRENT PUBLIC-TUNNEL DEMO ENVIRONMENT.** Synthetic and demo data only.

The Expo/LAN/public-tunnel demo is an unauthenticated development surface. Treat every payload as potentially reachable by anyone who can hit the tunnel URL.

## Current controls (implemented in code or configuration)

These exist only where the code or local configuration actually supports them:

| Control | Where it exists today |
| --- | --- |
| Backend-only OpenAI API key | `OPENAI_API_KEY` is read by the FastAPI process. The mobile app has no provider SDK and no provider key. |
| No direct mobile → OpenAI calls | Mobile talks only to `/api/v1/demo/*` via `apps/mobile/src/lib/api/client.ts`. |
| `store=False` on Responses calls | `OpenAIModelGateway` passes `store=False` to `responses.parse`. |
| Structured outputs | Responses API `text_format=DailyWinDraft`. |
| Schema validation | Pydantic `DailyWinDraft` plus application skill-contract checks before persist. |
| Material/skill allowlists | Context supplies `allowed_materials` / `allowed_skill_codes`; application code rejects unknown codes and off-list materials. |
| Deterministic safety validation | `validate_daily_win_safety` is application-owned. Model `safety_flags` cannot override it. Failed drafts are not persisted. |
| Bounded AI context | Nickname, latest baseline snapshot, InstructionPlan, ≤6 recent event summaries, ≤3 recent titles, allowlists. |
| Database IDs excluded from model context | `DailyWinModelContext` has no IDs. IDs live in internal `ai_runs.context_manifest` only. |
| Raw prompts/model responses excluded from `ai_runs` | `ai_runs` stores versions, token counts, latency, sanitized `error_code`, and ID manifests — not prompt text or completions. |
| Sanitized errors | Client messages are fixed strings. Development may include allowlisted `error_code` and allowlisted `dev_reason` (safety rule code only). Production omits both. |
| Canonical evidence separate from model inference | Parent feedback is stored, then converted to `learning_events`. Derived `learner_skill_state` is a projection, not the ledger. |
| Deterministic learner-state projectors | `trend_projector_v1` (persistence) and `academic_projector_v1` (academic bands). |
| Instructional decisions in application code | `InstructionPlanner` persists reason codes on `instruction_plans`. The LLM does not choose the target skill. |
| Optional DecisionGateway | Typed inferences only. Fake in tests. Not a live Jev/TypeSafe dependency. Must not write canonical learner state. A live decision vendor would be an additional subprocessor — do not send real child data until privacy, retention, contract, and production approval exist. Prefer plan+draft verification payloads with no child identity. |
| Evidence lineage | `learner_skill_state_evidence` plus `daily_win_id` / `daily_win_feedback_id` on events. |
| Prompt/model/schema/algorithm versioning | Prompt version, input/output schema versions, projector version, and model name are recorded on `ai_runs`. |
| Household/child composite ownership constraints | Child-owned rows use `(child_id, household_id) → children(id, household_id)`. |
| Demo routes absent in production | Demo router is registered only when `APP_ENV` is `local`, `development`, `dev`, or `test`. |
| Synthetic development data | Hayes preset plus custom synthetic onboarding. QA fixtures Nova/Milo/Riley exist for tests/eval only. Not real children. |
| No unrestricted child chatbot | Product loop is parent-operated. There is no child-facing chat endpoint. |
| Minimized child-data collection | V0.2 stores nickname, age band, grade, parent-reported interests/strengths/difficulties/motivators/response, preferred minutes, goals, generated Daily Wins, structured parent feedback, and derived state. Forbidden PII fields are rejected. No photos, location, school records, or open chat logs. |
| Development demo-session isolation | `X-Demo-Session` maps a SHA-256 hash to an isolated synthetic household. A session may exist before child setup. This is **not** authentication. |
| Optional moderation interface | `ContentModerator` exists and is **off** by default (`CONTENT_MODERATION_ENABLED=false`). Domain activity safety remains application-owned. |

## Not yet implemented (do not claim these exist)

- Production authentication
- Household membership authorization
- PostgreSQL Row-Level Security (RLS)
- Production rate limiting / WAF
- Cloud KMS / secrets manager
- Production database encryption configuration
- Production encrypted backups
- Formal deletion workflow
- Formal data-retention scheduler
- Zero Data Retention (ZDR) / Modified Abuse Monitoring (MAM)
- Production audit trail
- Security monitoring / alerting
- Penetration testing
- SOC 2
- Production incident-response process

CORS is currently wide-open (`allow_origins=["*"]`) on the development app so Expo/LAN can call the API. That is a development convenience, not a production control.

## Layered safety architecture (intended)

1. **Prompt / activity-generation boundaries** — generator prompt forbids hazardous activities and caregiver/pronoun invention.
2. **Strict structured-output schema** — `DailyWinDraft` field lengths, LEARN/DO/GROW order, material enum.
3. **Material / skill / domain allowlists** — application rejects unknown codes and materials.
4. **Daily Win domain-specific physical/activity safety validator** — deterministic rules with stable codes (`sharp_object`, `jumping_from_height`, …). `error_code` remains `unsafe_content`. Development may expose `dev_reason=<rule>`; never raw text, regex, or profile.
5. **General harmful-content moderation before production** — interface exists; not enabled in V1. Do not add a second generative model call for this.
6. **Persist / display only after validation passes** — rejected generations record a sanitized `ai_runs` row and do not write `daily_wins`.

Prompt instructions are not a security control. Authorization, tenancy, and physical-activity safety are application responsibilities.

## OpenAI data handling (accurate, current)

- Responses API calls set `store=False`.
- OpenAI states that API data is not used to train their models by default unless an organization explicitly opts in.
- **`store=False` does not itself guarantee zero provider retention.**
- Standard API abuse-monitoring logs may retain customer content according to [OpenAI's data controls and retention policy](https://platform.openai.com/docs/guides/your-data). Daily Win has **not** configured or been approved for Zero Data Retention.
- **Do not claim Daily Win currently has Zero Data Retention.**
- Evaluate ZDR / Modified Abuse Monitoring **before** sending real child production data.

## Production security roadmap (document only — not implemented in this task)

### P0 — before real child data

- Real parent authentication
- Server-side household authorization
- HTTPS only
- Production secret manager
- Encrypted managed PostgreSQL and backups
- PII-redacted logs
- Deletion workflow
- Written retention policy
- OpenAI ZDR/MAM evaluation and configuration
- Dependency and secret scanning
- Rate limiting
- Legal/privacy review for COPPA

### P1 — before public scale

- PostgreSQL RLS as defense-in-depth
- WAF / abuse controls
- Centralized audit logs
- Monitoring and alerting
- Backup restore drills
- Access / key rotation
- SAST / DAST
- Vulnerability management
- Penetration test
- Incident-response process

### P2 — enterprise / school sales

- FERPA-specific controls and contracts
- Vendor / subprocessor review
- Administrative RBAC
- Organization audit features
- SOC 2 readiness / audit
- Formal security policies and access reviews
