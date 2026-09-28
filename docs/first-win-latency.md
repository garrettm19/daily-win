# First-Win latency, onboarding pregeneration, Terra calibration (V0.4.2 / V0.4.2a)

The returning-parent path should already skip Terra. This document is the first-Win architecture and the Terra delivery-configuration record. It is not a marketing claim. Luna is not revisited. Global reasoning effort stays medium.

## Old first-Win flow

Profile setup committed → Home showed Generate → parent tapped → synchronous Terra (median ~31s in V0.4.1) → Win appeared.

## New first-Win flow

1. Canonical profile and goals commit.
2. `NextWinPreparation` starts with `trigger=first_profile_setup` (same scheduler, placement, planner, CoachProtocol, prompt v5, renderer contracts, validator as manual generate).
3. A STARTED `ai_runs` row is committed so Home can poll `generating`.
4. Parent sees a skippable 3–4 screen Guide intro. Generation continues independently.
5. Home: READY Win immediately, or today's focus + coach card + "Building today's challenge..."
6. Failure: onboarding still completes. Home: "Couldn't prepare today's Win. Try again." Profile is kept. Retry is the synchronous fallback.

Do not generate from incomplete onboarding fields. Do not trigger on PATCH while the parent is still editing. Goal/fingerprint invalidation still drops unused READY content.

## Duplicate / race handling

Child `SELECT … FOR UPDATE`. Recent STARTED runs block a second HTTP generate (`generation_in_progress`). Pregeneration jobs may supersede leftover STARTED. Reflection and first-profile-setup reuse an unreflected READY Win. Manual generate against that Win returns `feedback_required`. Tests keep background jobs off so TestClient cannot touch `SessionLocal`.

## User-visible wait

```
visible_wait_ms = max(0, raw_model_ms - onboarding_ms)
ready_before_guide = true when visible_wait_ms == 0
```

Unknown if Guide dwell was not recorded. Do not lengthen Guide screens to hide Terra. Skip is always available.

Development traces: `HOME TRACE`, `FIRST WIN TRACE`, Learning QA First-Win timing.

## Terra configuration

| Knob | Background prep | Interactive wait |
| --- | --- | --- |
| Model | `gpt-5.6-terra` | `gpt-5.6-terra` |
| Prompt | v5 | v5 |
| Reasoning effort | `medium` | `medium` |
| Requested service tier | `default` | `fast` |
| Returned service tier | `default` | typically `priority` |

`build_model_gateway` does not take these kwargs. `ai/delivery.py` binds them per intent. Persist `requested_service_tier` and `returned_service_tier` on `ai_runs.context_manifest`.

## Policy (V0.4.2a)

Background pregeneration: Terra `medium` + Standard (`default`).

Synchronous fallback while the parent is blocked: Terra `medium` + Fast request (`fast`; returned tier may be `priority`). Same scheduler, planner, CoachProtocol, prompt v5, schema, contracts, and safety. Only the service tier differs.

`none` is not a production reasoning setting unless a completed human draft review shows no quality loss. The V0.4.2 live JSON did not persist draft text, so `none` stays rejected on quality grounds.

`build_model_gateway` still does not take reasoning, tier, or intent kwargs. Selection lives in `ai/delivery.py`.

Blind review artifact: `--expand-terra-review` rebuilds A/B/C markdown from stored metrics plus frozen plans. `--terra-priority --live` is exactly 3 medium+fast calls.

## Output length

See the `output_audit` object in the Terra-config JSON. Do not quality-blind shorten every field. Schema cuts need fixture coverage.

## V0.4.2 live Terra calibration (n=3 per cell, do not overstate)

Artifact: `apps/api/eval-results/20260921T201524Z-terra-config-live.json` (12 live calls). Production reasoning was not switched globally.

| Configuration | median provider | contracts/safety | notes |
| --- | --- | --- | --- |
| Terra none/default | 16.9s | pass | Fewer output and 0 reasoning tokens. Drafts not stored. Keep medium. |
| Terra low/default | 25.8s | pass | Not meaningfully faster than medium. |
| Terra medium/default | 26.4s | pass | Background production default. |
| Terra low, request `fast` | 10.8s | pass | Response `service_tier` was `priority` on all 3. |
| Terra medium, request `fast` | 16.2s | pass | Returned `priority` on all 3. n=3 (9.4 / 16.2 / 25.5s). Interactive fallback. |

Artifact: `apps/api/eval-results/20260921T203953Z-terra-medium-priority-live.json` (exactly 3 additional live calls). Production global reasoning effort was not changed.
