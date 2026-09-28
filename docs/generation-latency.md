# Generation latency and next-Win pregeneration (V0.4.1)

A returning parent should almost never wait for Terra. This document is the architecture and measurement record. It is not a marketing claim.

Terra remains the default renderer. Educational policy is unchanged. No Redis, Celery, Kafka, or extra telemetry stack.

## Product latency budgets (internal)

| Path | Target |
| --- | --- |
| READY Win Home load | p50 < 500 ms backend, p95 < 1 s backend |
| Reflection submit | < 1 s excluding unusual DB/network |
| First-ever Win | pregenerate after committed profile; skippable Guide; remaining wait = Terra − onboarding |
| Normal returning parent | no synchronous model call |

## Generation trace

Development generations log a `GENERATION TRACE` (no secrets, no raw prompt) and persist timings on `ai_runs.context_manifest.latency`:

- `total_ms`
- `context_build_ms` / `session_lookup_ms`
- `scheduler` / `planner` / `coach_protocol`
- `prompt_context`
- `provider_ms`
- `validation_ms`
- `persistence_ms`

Also recorded: attempt count, model, prompt version, tokens, optional cached input tokens, optional reasoning/service-tier fields, trigger, sanitized failure code.

Learning QA **Generation performance** answers: is the wait OpenAI or our backend?

## Next-Win preparation

After a successful reflection:

1. Feedback and canonical events commit.
2. Learner state rebuilds.
3. The HTTP response returns. Terra is not on this path.
4. `NextWinPreparation.prepare_next_win` is scheduled through `schedule_prepare_after_reflection`. FastAPI `BackgroundTasks` is the current demo runner. Educational logic does not import FastAPI.
5. The validated Win is persisted `status=ready` with InstructionPlan, CoachProtocol, fingerprint, and `generated_after_reflection`.

Home `GET /api/v1/demo/next-win-state` never calls OpenAI.

| Home case | Behavior |
| --- | --- |
| Valid READY Win | return immediately |
| Preparation in flight | `generating` + deterministic stage copy; poll; no duplicate generate |
| Failed / invalidated | retry |
| First-ever / no prep | first profile setup now pregenerates; leftover Generate is retry/fallback |

Do not pre-generate tomorrow before today's reflection. Stale learner state would make tomorrow's Win a guess.

## READY Win validity (`plan_fingerprint_v1`)

SHA-256 of educational inputs (not public IDs): child academic/engagement baseline fields that the renderer and planner use, active goals and priority, evidence watermark (count + latest event time), curriculum / scheduler / placement / instruction-policy / prompt versions.

**Invalidate** unused READY content when those inputs change: active goals or priority, baseline academic context, interests/motivators/strengths/difficulties/minutes (`response_to_difficulty` included because it is parent-reported coaching context sent to the renderer), activity-history reset, demo restart, policy/prompt/curriculum version change.

Interests **do** invalidate. Engagement rendering uses them; showing a soccer-themed prepared Win after the parent switched to dinosaurs would be educationally stale wrapping, not a cosmetic no-op.

Historical Wins without a fingerprint stay valid (compatibility).

## Duplicate protection

`SELECT … FOR UPDATE` on the child row, plus: reflection-triggered generate reuses an existing unreflected READY Win; manual generate against that Win returns `feedback_required`. Tests disable background jobs so TestClient cannot touch `SessionLocal` outside the savepoint.

## Failure and retry

Pregeneration may retry once for provider/schema/renderer-transient codes, then `failed`. Reflection still succeeded. Next Home visit can retry. Unsafe content does not retry in the outer loop.

## Loading UX

No fake percents. Stages only when they match backend state: choosing focus, building the challenge, checking the activity.

First-ever Home can show today's planner focus and CoachProtocol bullets before Terra finishes.

## Weekly report vs Home

Weekly summaries rebuild on the Week route, not on Home. Home does not wait on weekly synthesis.

## Distinguishing Terra vs tunnel

Backend `GENERATION TRACE` / `HOME TRACE` / `backend_elapsed_ms` is server time. Phone wait minus that remainder is Expo/Cloudflare/local networking.

## Reasoning effort and service tier

`OpenAIModelGateway` accepts optional `reasoning_effort` and `service_tier`. `build_model_gateway` does not take those kwargs. `generate_demo_daily_win` binds a `GenerationDelivery` at the gateway boundary:

- `BACKGROUND_PREP`: reasoning `medium`, request `default`
- `INTERACTIVE_WAIT`: reasoning `medium`, request `fast` (GPT-5.6 responses may return `priority`)

Background jobs, reflection pregeneration, and normal next-Win preparation use `BACKGROUND_PREP`. Retry after prep failure and other UI-blocked generate paths use `INTERACTIVE_WAIT`. Do not change global reasoning effort. Terra stays the renderer.

Live commands (synthetic only, spend budget only when intended):

```
uv run python -m daily_win_api.eval --suite latency
uv run python -m daily_win_api.eval --latency-baseline
uv run python -m daily_win_api.eval --latency-baseline --live
uv run python -m daily_win_api.eval --terra-config
uv run python -m daily_win_api.eval --expand-terra-review
uv run python -m daily_win_api.eval --terra-priority --live
```

Maximum live baseline: five Terra calls (introduce, diagnostic, practice, remediation, review) on frozen InstructionPlans.

Maximum Terra config live calls: 9 reasoning-effort + 3 service-tier = 12. Production config is not changed automatically.
