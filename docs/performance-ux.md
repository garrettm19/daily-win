# Performance UX — V0.4.5

Parent-facing presentation only. Educational intelligence is unchanged: `curriculum_v2`, `placement_policy_v1`, `instruction_scheduler_v1`, `instruction_policy_v4`, projectors, CoachProtocol, mastery thresholds, review timing, prompt v5, Terra, and evidence semantics are frozen.

## Why there are no fake competency scores

Existing evidence supports **stage**, **recent support**, **session count**, and **trend**. It does not support IQ, grade percentile, peer rank, “learning score,” or percent mastery. Internal indexes (`not_observed=0` … `retained=4`) may position a stage indicator. They are never shown as a validated number.

## Competency stage visualization

Bands: Not observed → Emerging → Developing → Demonstrated → Retained.

Home and Progress render filled dots for the current band plus the parent label. Dots are ordinal markers, not equal psychometric distance, and not “3/5 mastery.”

## Independence trend semantics

Plot discrete check results, oldest → newest:

- Independent
- Light help
- Significant help
- Not yet (incorrect / not attempted)

No interpolation, no continuous learning curve. Allowed captions: “Needing less help recently,” “Recent results are mixed,” “Still gathering evidence,” “Independent in the last two checks,” “Needed more support last session.”

Every chart has that text. Meaning is never chart-only.

## Home hierarchy

1. Child nickname + date + short status
2. **Today** — one dominant Daily Win card
3. **Progress** — compact active skill cards
4. **Latest result** — one fact from the last check
5. **Next move** — planner/scaffold intent (`one_thing_to_improve` / what changed / current adjustment)
6. Week / History / Profile links

Recent Observation is not on Home. It duplicated Progress/Result and was glitchy. Progress skill cards carry the same evidence more clearly.

## Silent READY behavior

Home captures the presented Win when the screen is focused.

If a **different** Win becomes READY while Home stays on screen, the visible card does not swap. The new READY payload is stored. It becomes the presented Win on the next intentional focus/re-entry (navigate away and back, pull-to-retry, Insight → Done when the parent returns).

First-run preparing → READY may complete the preparing card (spinner → ready). Replacing an already-visible Win with another Win may not.

Ownership:

- **Current Win** — presented unreflected activity
- **Next Win** — `next-win-state` payload, possibly not yet presented
- **Historical Win** — `daily-win?id=` with feedback; read-only detail
- **Prepared next** — generating/ready behind the presented card

## Session stepper

Mission → Learn → Do → Grow → optional Bonus → Result.

Mission shows skill, duration, materials, game plan, Begin. Assessment copy, GROW, bonus, and reflection wait until their step. Learn/Do/Grow number actions; Watch for is a coach metric on Do, not an assessment block. Sticky Back/Next on action steps only.

## Result presentation

After reflection: Session complete + Independence / Challenge / Self-correction / Persistence **only when collected**, then what changes next. No composite score.

## Historical vs current vs next

History detail: date, title, skill, result. No “Today’s Win,” “Today’s Focus,” Start, or live preparation state.

## Remaining presentation limits

- No screenshots were captured in this pass (no device farm). Manual device QA still required.
- Sticky session controls are used on action steps; Mission and Result keep in-flow buttons so small phones are not covered.
- Challenge-fit timeline is encoded in Result/History (too easy / about right / too hard), not a second Home chart.
