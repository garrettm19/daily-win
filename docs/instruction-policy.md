# Daily Win — Instruction policy

Current planner: `instruction_policy_v4`. Frozen scheduler-less fixtures: `instruction_policy_v3`. Historical plans may also be `instruction_policy_v1` or `instruction_policy_v2`. Scheduler: `instruction_scheduler_v1` (see [instruction-scheduling.md](instruction-scheduling.md)). Placement: `placement_policy_v1` (see [placement-calibration.md](placement-calibration.md)).

The InstructionPlanner is application-owned. It runs **before** ModelGateway. Prompt v5 treats its output as authoritative. PlacementPolicy chooses the diagnostic entry when evidence is sparse; the planner does not hide age heuristics inside the prerequisite walk.

## Inputs

- Active parent goals (priority order)
- Age/grade and preferred duration (from baseline)
- Derived academic snapshots and persistence signal
- Prerequisite graph
- Recency / review (`due_for_review`)
- Recent primary skill codes and recent Daily Win titles
- Interests (engagement constraints only)

## Outputs (`InstructionPlan`)

Persisted on `instruction_plans` (queryable columns + versioned JSONB `plan`):

- `primary_skill_code` and optional `supporting_skill_code`
- `selection_reason_codes`
- `instruction_mode`: `introduce` | `practice` | `review` | `remediation` | `diagnostic`
- `intended_difficulty`: `reduce` | `similar` | `slightly_increase`
- `scaffold_level`: `three_step_visual` | `one_prompt` | `independent_try`
- `prerequisite_rationale`
- `assessment_objective` and required `assessment_probe`
- `desired_evidence`
- optional `growth_target_code` and `growth_adaptation_summary`
- `duration_minutes` (clamped 10–25)
- `engagement_theme_constraints` (up to two interests)
- `recent_themes_to_avoid`
- `policy_version`, `academic_band`
- `placement_policy_version`, `placement_entry_label`, `placement_why`, `presentation_constraint`

No chain-of-thought.

## Age / grade policy

Age/grade is a **starting prior**, not mastery. It does not write learner bands and does not permanently skip prerequisites.

`PlacementPolicy` (`placement_policy_v1`) selects an age/grade-appropriate diagnostic entry when the selected strand has no usable Daily Win evidence. Unknown (`not_observed`) is not treated as weakness. Observed weakness still steps down one prerequisite and still blocks advancement.

Age/grade also influences wording/context and whether an older child on a foundation skill gets an `age_respectful_foundation` renderer contract.

Sparse academic placement uses `diagnostic` from age 7 and `introduce` for younger children, always at the grade-band entry skill rather than the earliest unknown prerequisite. Diagnostic success is ordinary evidence.

## Selection algorithm (deterministic)

`instruction_policy_v4` receives a `ScheduledFocus` from `instruction_scheduler_v1`. The planner no longer always starts at parent academic #1. Frozen `instruction_policy_v3` still starts at the highest-priority academic goal.

1. Take the scheduler's selected academic goal (`v4`) or the highest-priority **academic** goal (`v3`); otherwise the first goal.
2. `PlacementPolicy` expands the strand and, if evidence is sparse, selects the highest grade-band entry skill for the child's age.
3. Unknown prerequisites do **not** recurse to the earliest leaf. Observed-weak prerequisites still gate.
4. If a later skill's diagnostic was weak (`emerging`, no independent success), step down one academic prerequisite (`foundation_review`).
5. Otherwise walk candidates in progression order for review, practice, introduce, or diagnostic using existing band rules.
6. Supporting academic skills are omitted during sparse diagnostics so a later skill cannot ride along.

Supporting skills must pass the same prerequisite gate. A later skill that could not be primary cannot be named as supporting. Growth/life overlays remain allowed as supporting.

Engagement preferences **cannot** override the instructional objective. Interests only constrain theme.

## Scaffold and difficulty

| Condition | Scaffold | Difficulty |
| --- | --- | --- |
| Remediation | `three_step_visual` | `reduce` |
| Diagnostic | `one_prompt` | `similar` |
| Introduce / emerging | `three_step_visual` | `reduce` |
| Developing or review | `one_prompt` | `similar` |
| Demonstrated / retained (no review/remediation) | `independent_try` | `slightly_increase` if retained, else `similar` |

Scaffold decreases only when the academic band or diagnostic mode warrants it. Independent success in a single session does not drop scaffold to independent-try.

## Growth overlay

If a growth/life goal is active, it becomes `growth_target_code`. Persistence still uses `AdaptationDirective` copy from `trend_projector_v1`. That overlay must not change the academic primary skill.

## Decision lineage example

```
primary_skill: writing.sentences.complete_sentence
reason_codes: [parent_priority, age_grade_appropriate, insufficient_independent_evidence]
instruction_mode: introduce
scaffold: three_step_visual
policy_version: instruction_policy_v3  # frozen fixture example; current plans are v4
prerequisite_rationale: Prerequisites are sufficiently evidenced or none apply.
```

Hayes’ parent #1 goal is the writing-organization **strand**. The planner therefore starts at `writing.sentences.complete_sentence` (prerequisite of `writing.organization.sequence_events`) until that skill is demonstrated or retained.

Age-9 Nova with an addition goal and no counting evidence gets a **diagnostic check of counting**, not a declaration that addition within 10 is mastered.

## Personalization split

| Instructional (code) | Engagement (LLM, constrained) |
| --- | --- |
| What to teach | Theme from interests |
| Difficulty | Motivators / playful framing |
| Scaffold | Age-appropriate wording |
| Review timing | Activity style |
| Assessment probe / success criteria | Concise coaching voice |
| Diagnostic vs introduce | Brief independent check vs first teaching session |

Instructional personalization always wins. A soccer theme does not change the target skill.

## Evaluation

Deterministic golden cases and why-not tests live in `apps/api/src/daily_win_api/eval/planner_cases.py`. Those fixtures evaluate frozen `plan_instruction_v3()` so `instruction_policy_v3` behavior does not silently change. Current generation uses `instruction_policy_v4` after `instruction_scheduler_v1`. Placement version `placement_policy_v1` is asserted on every case. See [planner-evaluation.md](planner-evaluation.md), [placement-calibration.md](placement-calibration.md), and [instruction-scheduling.md](instruction-scheduling.md). Changing selection order, gates, or scaffold/difficulty mapping requires a new policy version, not a silent rewrite of stored plans.
