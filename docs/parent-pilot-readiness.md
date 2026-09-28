# Parent pilot readiness — V0.4.5

Date: 2026-09-21. Educational intelligence frozen. This pass is live-pilot bug fixes and performance-dashboard presentation, not V0.5.

See `docs/performance-ux.md` for presentation rules.

## Live bugs (blockers)

| Bug | Status |
| --- | --- |
| Reflection “How did the check go?” run-on | **FIXED** — caption is canonical `SUPPORT_CAPTION` only. Option labels stay the five deterministic check results. Generated `prompt_label` / `support_caption` are not concatenated into the control. Tests: `academicLoop.test.ts`, `displayNormalize.test.ts`. **VERIFIED** in unit tests. Device tap-through still Mason. |
| Historical “Today’s Win” / “Today’s Focus” | **FIXED** — `daily-win?id=` with feedback uses `HistoryDetail` (date, title, skill, result). No Today labels. History dates use `formatHistoryDate`. Tests: `parentCopy.scan.test.ts`, `sessionSteps.test.ts`. **VERIFIED** in unit tests. |
| Recent observation glitch | **FIXED** — unmappable events omitted; frontend `formatObservation` hides snake_case / `[object Object]` / `Goal` / `Parent observation`. Section removed from Home (redundant). Progress uses skill cards. Tests: `competency.test.ts`, `test_v045_presentation.py`. **VERIFIED** in unit tests. |
| READY replaces Home mid-read | **FIXED** — `shouldHoldPresentedWin`; poll stores READY but does not swap the presented Win until next Home focus. Tests: `homePresentation.test.ts`. **VERIFIED** in unit tests. Device: stay on Home while next Win finishes. |

## 1–25 (carry-forward from V0.4.4)

Pilot-preflight, fresh-start, Guide, first-Win prep, READY returning without a model call, coach cards, materials, reflection timing, Insight Done, next-Win background prep, reset/restart, session isolation, Parent Pilot View + five-tap restore: unchanged in policy. Presentation of Home / Daily Win / Progress / Week / Result is V0.4.5.

## Device QA (Mason)

- [ ] Home while next Win finishes in background — no card replacement
- [ ] Historical Win details — no Today’s Win / Today’s Focus
- [ ] Reflection — five short canonical check choices
- [ ] Recent observation — absent on Home; Progress skill cards clean
- [ ] Long Daily Win — step-based, not one document
- [ ] Progress — skill stage visible without a paragraph
- [ ] Three sequential Wins — independence dots become useful
- [ ] Result — outcome in under ten seconds

## Tests

Mobile: `npx tsc --noEmit` clean. `npx expo lint` clean. `npm test` **98 passed** (was 73).

Backend: `uv run ruff check .` clean. `test_v045_presentation.py` **2 passed**. Full `pytest`: **354 passed, 10 failed**. The 10 failures are unfiltered table counts (`DailyWinFeedback` / `LearningEvent` expected 0 or 1, saw ~3) from leftover committed demo rows in local Postgres, not from this presentation change. Same pattern as a dirty live-pilot database; tests roll back their own writes but still see other sessions’ committed rows.

No eval batch. Educational policy untouched.

## Unresolved HIGH

Screenshots were not captured in-agent (no consistent device viewport). Manual screenshots still recommended. Sticky session footer not proven on the smallest iPhone; Mission/Result keep in-flow buttons.

Hardware-only checks from V0.4.4 remain: small iPhone, Dynamic Type, iOS back, process death, brief network drop, Cloudflare URL change.

## Unresolved BLOCKERS

None in software for the four live bugs, given unit verification. Live preflight still needs API process + tunnel if used.

PARENT PILOT READY: YES

## Before parent test

[ ] database running
[ ] API running
[ ] tunnel/API URL valid
[ ] Metro running
[ ] development build opens
[ ] pilot-preflight passes
[ ] fresh tester reset
[ ] Parent Pilot View enabled
[ ] phone charged
[ ] no Learning QA visible

Then: HAND OVER THE PHONE.

Do not explain the interface.

Observe.

STOP.
