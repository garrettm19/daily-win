# Longitudinal simulation

Offline, deterministic stress-test of the real learning engine.

Command:

```
uv run python -m daily_win_api.eval --suite longitudinal
```

Also included in `--suite all`. Does **not** call OpenAI / Terra.

## What is real

The simulator calls the production:

- `placement_policy_v1`
- `instruction_policy_v4` with frozen `instruction_policy_v3` comparison
- `instruction_scheduler_v1`
- `curriculum_v2`
- `academic_projector_v1`

It accumulates `AcademicEvidence` and rebuilds bands with `project_academic_band`. It does **not** write `learner_skill_state` directly. Renderer/Terra is not invoked.

## Archetypes

| Id | Name | Intent |
| --- | --- | --- |
| A | Fast progressor | Usually independent |
| B | Typical progressor | Prompted, then independent |
| C | Foundational gap | Weak grade-level diagnostics, then teach where it holds |
| D | Inconsistent | Independent / independent / incorrect |
| E | Low persistence / strong academics | Independent answers, weak setback response |
| F | Strong persistence / weak academics | Keeps trying, still incorrect |
| G | Sparse | 1 Win/week |
| H | Frequent | 5 Wins/week |
| I | New older (age 9) | Grade-aware diagnostic |
| J | New younger (age 5) | Introductory placement |
| K–M | Goal conflicts | Writing vs spelling gap; advanced math with weak prereqs; spelling+math+persistence |

Horizons: 4 / 12 / 24 weeks at 1 / 3 / 5 Wins per week (not every combination).

## Anomaly flags

`SKILL_LOOP`, `PING_PONG`, `PERMANENT_FOUNDATION_LOOP`, `UNDER_ADVANCEMENT`, `REMEDIATION_TRAP`, `REVIEW_OVERLOAD`, `REVIEW_STARVATION`, `GOAL_STARVATION`, `GROWTH_DOMINANCE`, `KINDERGARTEN_DUMP`.

Severity: CRITICAL fails the eval suite. HIGH/MEDIUM/LOW are reported findings.

## Intentionally not redesigned

- Mastery thresholds
- Spacing intervals (`REVIEW_AFTER_DAYS = 14`, retained spacing = 7)
- Curriculum progression
- Terra / renderer

V0.3.8 added `instruction_scheduler_v1` so academic priority #1 is a preference, not a monopoly. See [instruction-scheduling.md](instruction-scheduling.md). `GOAL_STARVATION` is now a scheduler invariant, not an accepted long-term finding.

## Recency behavior (existing)

`academic_projector_v1` has **no decay mathematics**. Old independent evidence still counts. One incorrect after two independents does **not** set `needs_remediation` (last two sessions must both be weak). Repeated recent weak sessions after independent success do.

## Query / scale notes

Hot-path indexes already exist:

- `ix_daily_wins_household_child_created`
- `ix_learning_events_occurred_at` (household, child, occurred_at)
- `ix_learning_events_child_skill_occurred`
- `ix_instruction_plans_household_child_created`
- unique `uq_daily_win_feedback_daily_win_id`

ContextBuilder is bounded (10 events, 6 summaries, 3 Wins) and does not grow linearly with history.

Learner-state rebuild reads all canonical assessment events for a skill. That is required so derived state is reconstructable. It is not a renderer-context leak. Do not add caching unless measurement shows a reason.

Concurrency: generation takes `SELECT … FOR UPDATE` on the child row, then refuses a second Win until feedback exists. Feedback is unique per Daily Win at the database.

## Reports

- `eval-results/longitudinal-engine-audit.md`
- `eval-results/<timestamp>-scheduler-audit.md`
- timestamped JSON beside them

## Integrity checks (pytest)

Lineage, rebuild, idempotent feedback, duplicate generation, provider-failure (no orphan InstructionPlan), projector rollback, activity-history reset.
