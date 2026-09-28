# Parent pilot acceptance — V0.4.4

A local parent pilot is READY only if every blocking item below passes. This is acceptance hardening, not educational redesign.

Educational intelligence stays frozen: `curriculum_v2`, `placement_policy_v1`, `instruction_scheduler_v1`, `instruction_policy_v4`, `academic_projector_v1`, `trend_projector_v1`, CoachProtocol, mastery thresholds, review spacing, prompt v5, Terra, reasoning, and service-tier policy.

## Blocking criteria

A parent who did not build Daily Win must be able to: start the app, understand what to do, complete one session, report what happened, come back later, and see that the system adapted.

| Blocker | Pass means |
| --- | --- |
| App starts cleanly | Development client opens without a crash |
| Backend/database reachable | `/health` and `/health/db` return 200 |
| Correct mobile API URL | `EXPO_PUBLIC_API_URL` has no trailing slash and reaches `/health` |
| First setup works | Hayes or custom profile saves and leaves first-run |
| Guide works | Four skippable screens; Skip intro; generation continues |
| First Win prepares | READY, preparing with known focus, or clear retry — never an empty spinner |
| Win renders | Title, ~20 min, materials, Your job today, Start Daily Win |
| Parent understands what to do | Actionable within ~10 seconds of Home READY |
| Reflection saves | Submit locks; answers survive failure; no duplicate evidence |
| Insight renders | What we learned + What changes next in ~10–20 seconds |
| Learner state updates | Progress/Insight change after a real reflection |
| Next Win is prepared | Parent can leave after Insight; background prep continues |
| Close/reopen | Process death recovers correctly |
| Returning READY | No model call; no Generate / No Win flash when a valid Win exists |
| Progress / History / Weekly | Load, empty, sparse, and filled states are understandable |
| Resets work | Start fresh parent pilot returns to first-run with no ghost data |
| No developer jargon | Parent Pilot View hides QA, fingerprints, codes, model names |
| No crashes / duplicate Wins / lost reflection | Rapid taps do not double-mutate |
| Network failure recoverable | Retry works; copy does not claim data was lost |

Do not declare READY if any blocking item fails.

## Severity

**BLOCKER** — crash, cannot generate, cannot save reflection, duplicate Win, stale learner state, wrong session, developer UI exposed, parent cannot understand the activity, invalid assessment flow, next Win not recoverable.

**HIGH** — major confusion, long unnecessary blocking, important CTA unclear, incorrect adaptation copy, weekly report misleading.

**MEDIUM** — awkward wording, extra scrolling, noncritical visual inconsistency.

**LOW** — minor spacing or cosmetic preference.

Fix BLOCKER and HIGH before `PARENT PILOT READY: YES`.
