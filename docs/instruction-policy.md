# Daily Win — Instruction policy

Policy version: `instruction_policy_v2`. Historical plans remain `instruction_policy_v1`.

The InstructionPlanner is application-owned. It runs **before** ModelGateway. Prompt v4 treats its output as authoritative.

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

No chain-of-thought.

## Age / grade policy

Evidence and prerequisites determine readiness. Age/grade does **not** fabricate mastery and does **not** skip foundational skills.

Age/grade **does** influence:

- wording and context (renderer)
- expected pace of the first check
- whether a foundational academic skill with **no evidence** uses a brief diagnostic probe instead of extended introduce/practice
- activity presentation

Rule: if the selected academic skill is `not_observed` and the child is age **8 or older**, mode is `diagnostic` (medium scaffold, similar difficulty, reason `diagnostic_check`). Younger children still get `introduce`. Diagnostic success is ordinary evidence. It is not inferred from age.

## Selection algorithm (deterministic)

1. Take the highest-priority **academic** goal; otherwise the first goal.
2. Expand strand goals to ordered child skills that are generation-supported. Age does not remove candidates.
3. Walk candidates in progression order:
   - Walk missing prerequisites **recursively**. A prerequisite is sufficiently evidenced only if band is `demonstrated` or `retained`.
   - If a prerequisite is missing, select that earlier skill. Mode uses the same `_mode_for` rules (remediation, diagnostic, introduce, or practice).
   - If `needs_remediation` is set, **remediation takes precedence** over the generic emerging/developing practice branch.
   - If the skill is due for review (≥ 14 days since last practice while demonstrated/retained), **review**.
   - If band is `not_observed` → `introduce` (age < 8) or `diagnostic` (age ≥ 8).
   - If band is `emerging` or `developing` (and not remediating) → **practice**.
4. If every candidate is beyond those gates, stay on the last skill (`progression_next`).

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
policy_version: instruction_policy_v2
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

Deterministic golden cases and why-not tests live in `apps/api/src/daily_win_api/eval/planner_cases.py`. Policy version `instruction_policy_v2` is asserted on every case. See [planner-evaluation.md](planner-evaluation.md). Changing selection order, gates, or scaffold/difficulty mapping requires a new policy version, not a silent rewrite of stored plans.
