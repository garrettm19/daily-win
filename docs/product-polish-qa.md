# Product polish QA — V0.4.3

Manual flows for the V0.4.3 polish pass. Do not treat this as a live OpenAI eval. Educational policy, scheduler, curriculum, and Terra are unchanged.

## Error recovery matrix

| Case | Expected parent message | Data | Retry |
| --- | --- | --- | --- |
| API offline / Cloudflare unavailable | Can't reach Daily Win right now. Check the connection and try again. | Existing Home/Progress/Weekly content stays when already loaded | Try again |
| Profile save failure | Couldn't save your changes. Nothing was lost. | Form stays | Try again |
| Generation failure | Couldn't prepare today's Win. Try again. | Profile intact | Try again |
| Priority fallback failure | Same generate copy; no provider names | Profile intact | Try again |
| Reflection save failure | Couldn't save the reflection. Your answers are still here. | Draft preserved | Save reflection |
| Home GET failure | Couldn't load Daily Win. Try again. (or unavailable copy) | Last known session kept when possible | Try again |
| Progress GET failure | Couldn't load Progress. Your Daily Wins are safe. | Progress stays if previously loaded | Try again |
| Weekly report failure | Couldn't load the Weekly Coach Report. Your Daily Wins are safe. | Report stays if previously loaded | Try again |

## Flows

### A. Brand-new custom age-9 profile → Guide → first Win → reflection → Insight

1. First screen states 20 minutes / one challenge / how to coach.
2. Create a profile (fictional). Goals show rotation copy. Duration is About N min.
3. Guide is four skippable screens.
4. Home shows today’s focus and Your job today if still preparing; no percentages or model names.
5. Start Daily Win; first actionable coaching is above the fold after Start.
6. What to check is unmistakable. Bonus is clearly optional.
7. Reflection is short, no snake_case, engagement only if useful.
8. Insight: Saved. What we learned. What changes next. Parent can leave.

### B. Returning parent with READY Win

Open Home. No generate interstitial. READY card is the Daily Win with Start Daily Win.

### C. READY Win invalidated by goal edit

Edit goals. Home shows rebuilding / Try again — not the stale Win and not “Your Win disappeared.”

### D. Reflection failure and retry

Turn the API off, tap Save reflection. Answers remain. Restore API, save, reach Insight.

### E. First-Win Terra slower than Guide

Finish Guide while preparing. Home stays on known focus + Preparing today's challenge... then transitions to READY without flashing empty.

### F. First-Win READY before Guide completed

Skip or finish Guide. Home shows the READY Win, not a generate CTA.

### G. Weekly Coach Report after 5 Wins

Week range is human (e.g. Sep 15 – Sep 21). Sections that have nothing are omitted. 1–2 bullets per section. One trust line.

### H. Progress with sparse evidence

Empty or “Not enough evidence yet.” No fake percentages. Next action is complete a Win.

### I. Progress with several academic states

Active skills first. Other skills we’ve seen is collapsed. Bands, not meters.

### J. Single academic goal + persistence

Hayes-style one academic goal. No Discovery Week card. GROW is present but quieter. Guide still makes sense.

### K. Multi-goal discovery profile

Getting to know their level shows domain labels, not a progress percent, not an exam.

### L. Optional Bonus skipped

Bonus copy: only if you both want one more challenge. Skipping does not block reflection.

### M. Optional Bonus completed

Bonus engagement can appear. Main Win still visually dominates.

### N. Long generated Win

Long title/steps wrap and scroll. CTA remains reachable. Empty optional fields do not render headers.

### O. Small-screen device

Top safe area, bottom CTA, keyboard on reflection notes, no trapped scroll. Check a short iPhone and a taller simulator.

## Production gating checklist

Production-facing UI must not show: Learning QA, tester fingerprint, raw error codes, policy versions, model names, reasoning effort, service tier, prompt version, debug latency, reset controls.

## Automated coverage added in this pass

- Home phases: READY vs generating vs failed vs invalidated
- Polling stops unless `generating`
- Guide is four short screens
- Reflection engagement is conditional
- Insight/Progress/Weekly empty-heading helpers
- Parent error copy for progress/weekly/offline
- Discovery hidden for a single domain
- Notice chips / job bullets / weekly bullets capped
