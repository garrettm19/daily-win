# Instruction scheduling (V0.3.8)

Policy version: `instruction_scheduler_v1`. Current planner: `instruction_policy_v4`. Frozen scheduler-less planner: `instruction_policy_v3`. Placement: `placement_policy_v1`. Curriculum: `curriculum_v2`. Review spacing: `REVIEW_AFTER_DAYS=14` (unchanged).

The scheduler is a transparent, deterministic application layer. It does **not** use an LLM, opaque optimization, percentages, or a mutable scheduler-state blob. Historical `InstructionPlan` rows keep the policy version they were stored with.

## Architecture

```
active academic goals
+ learner state
+ recent instructional history
+ remediation / diagnostic urgency
+ review-due state
        ↓
InstructionScheduler (instruction_scheduler_v1)
        ↓
ScheduledFocus
        ↓
InstructionPlanner (instruction_policy_v4)
        ↓
InstructionPlan
```

Separation:

| Layer | Owns |
| --- | --- |
| `InstructionScheduler` | **Which academic goal/strand** gets today's slot |
| `InstructionPlanner` | Exact skill, mode, scaffold, difficulty, probe, growth overlay |
| `PlacementPolicy` | Diagnostic entry skill when evidence is sparse |
| Renderer / Terra | Experience only. Not the instructional objective |

Growth goals such as persistence are **overlays**. They never consume an academic scheduling slot.

Discovery week (V0.4.0) works *with* this scheduler: unsampled diagnostic academic goals rotate after one Win so no single domain monopolizes first signals. See `docs/guide-mode.md`.

## ScheduledFocus

Persisted on the `InstructionPlan` JSON (no new tables):

- `selected_goal_code` / selected strand
- `selection_reason_codes`
- `urgency_class`
- `recent_goal_history`
- `deferred_goals`
- `review_due`
- `starvation_guard_triggered`
- `scheduler_version`
- `scheduler_why_selected` / `scheduler_why_deferred`
- `application_variant` (`transfer` for retained-terminal reviews)

No chain-of-thought.

## Priority semantics

`#1`, `#2`, and `#3` are parent instructional priorities, **not** a monopoly.

| Rank | Meaning |
| --- | --- |
| #1 | Strongest scheduling preference when urgency is comparable |
| #2 | Important secondary instructional priority; must receive periodic slots |
| #3 | Lower but still active; not dropped unless educationally blocked |

All active **academic** goals receive opportunities over a long enough horizon unless blocked by an explicit educational reason (for example the goal is maintenance-only, or another goal is in short-lived remediation/diagnostic).

## Urgency classes

Highest educational urgency first:

| Class | When |
| --- | --- |
| `active_remediation` | Recent evidence indicates genuine weakness (`needs_remediation`) |
| `unresolved_diagnostic` | Placement still uncertain / sparse evidence |
| `active_learning` | Normal current instructional work |
| `review_due` | Previously demonstrated/retained skill is due (`REVIEW_AFTER_DAYS=14`) |
| `maintenance` | Retained skill is not currently due |

Review-due is a **candidate**, not an automatic selection.

## Scheduling rules

Documented thresholds, chosen because they are understandable and then checked in simulation (not reverse-engineered to a pretty percentage):

| Rule | Value | Effect |
| --- | --- | --- |
| `CONSECUTIVE_FOCUS_LIMIT` | 3 | After three consecutive Wins on the same eligible goal, rotate to the next eligible academic goal |
| `MAX_GOAL_NEGLECT_WINDOW` | 4 | An eligible non-maintenance goal neglected this long triggers `GOAL_STARVATION` / `secondary_goal_starvation_guard` |
| `REMEDIATION_PREEMPT_CAP` | 5 | Remediation may temporarily override rotation, but not forever. The neglect window can interrupt earlier when another academic goal is waiting |
| `DIAGNOSTIC_PREEMPT_CAP` | 2 | Cold-start diagnostics get a short priority, then rotation resumes |
| `REVIEW_LOAD_WINDOW` | 3 | Look at the last three Win modes |
| `REVIEW_LOAD_MAX` | 1 | If that window already contains more than one review, prefer active learning when it exists |
| `REVIEW_COOLDOWN_WINS` | 3 | Do not immediately revisit the same retained review target |

Reason codes include `highest_priority`, `secondary_goal`, `unresolved_learning`, `unresolved_diagnostic`, `remediation_urgency`, `secondary_goal_starvation_guard`, `consecutive_focus_limit`, `new_goal_needs_placement`, `review_candidate`, `review_load_guard`, `review_cooldown`, `maintenance_only_candidate`, `no_active_learning_candidate`.

## Starvation guard

For every active academic goal the scheduler tracks last selection (from recent InstructionPlans), consecutive focus, and neglect. `GOAL_STARVATION` is a scheduling invariant: an eligible active academic goal ignored beyond `MAX_GOAL_NEGLECT_WINDOW` must be selected next. Scheduler eval fixtures fail if that guard does not fire. Longitudinal simulation also flags `GOAL_STARVATION` when priority #2 is absent or neglected for more than six Wins.

## Remediation and diagnostic scheduling

Remediation may temporarily preempt rotation. Strong later independent evidence returns the skill to practice / demonstrated / retained, and the scheduler restores multi-goal balance. Remediation cannot remain an indefinite monopoly after recovery.

Cold-start diagnostics are also temporary. Once placement has usable evidence, `unresolved_diagnostic` disappears. The scheduler does not keep choosing diagnostic tasks merely because the learner is new.

## Terminal-skill behavior

A retained terminal leaf (for example `writing.spelling.multisyllabic_irregular` when it is the top generation-supported skill) must not remain in ordinary repeated `practice` forever.

| State | Behavior |
| --- | --- |
| `ACTIVE_LEARNING` | Ordinary introduce / practice / diagnostic |
| `MAINTENANCE` | Repeated practice stops; another active academic goal receives the slot |
| `REVIEW_DUE` | Occasional review of the **same** canonical skill |

`instruction_policy_v4` therefore:

- does not auto-select an intra-strand `due_for_review` skill unless the scheduler urgency is review/maintenance
- returns `REVIEW` plus `terminal_maintenance_transfer` / `terminal_transfer_review` instead of endless `PRACTICE` on a retained terminal leaf

Renderer variation is allowed (`application_variant=transfer`): apply the same retained spelling skill in a short sentence, edit, or writing challenge. Do not invent a harder skill or a fake mastery level.

## Review queue

`due_for_review` means the skill **may** be reviewed, not that today **must** be a review.

The scheduler considers:

- how overdue the review is (via urgency class, still using 14-day spacing)
- active-goal neglect
- current remediation
- last review target
- recent review frequency (`REVIEW_LOAD_WINDOW` / `REVIEW_LOAD_MAX`)

If the last three Wins already contain more than one review and a meaningful active-learning candidate exists, schedule active learning. Only schedule another review when no meaningful active-learning candidate remains (`no_active_learning_candidate`).

`REVIEW_AFTER_DAYS` stays 14. V0.3.8 separates **when a skill becomes due** from **whether today should be used for that review**. Spacing should be changed only if overload remains after this candidate/cap behavior.

## Ping-pong prevention

Track recent review targets. Before revisiting the same retained skill, apply `REVIEW_COOLDOWN_WINS` unless fresh weak evidence makes the skill remediation rather than review. This is meant to stop A/B review ping-pong when meaningful active learning exists elsewhere.

## Goal change, new goals, retained #1

Scheduler history remains valid when the parent reorders goals. Future scheduling uses the new priority order. Evidence is not erased. Placement is not restarted unless the new goal actually lacks evidence.

A newly added academic goal receives `new_goal_needs_placement` rather than waiting indefinitely behind an already-retained #1.

If goal #1 is broadly retained/maintenance-only and goal #2 still has active learning, goal #2 receives most active-learning slots. Parent #1 still influences review/maintenance, but does not force repetitive retained work.

## Policy regression

| Version | Role |
| --- | --- |
| `instruction_policy_v3` | Frozen scheduler-less behavior. Golden planner fixtures and `plan_instruction_v3()` |
| `instruction_policy_v4` | Current production path: scheduler + no intra-strand review steal + terminal maintenance |
| `instruction_scheduler_v1` | Current scheduler |

New plans record both `instruction_scheduler_v1` and `instruction_policy_v4`. Historical plans are unchanged. `plan_from_dict` treats missing scheduler fields as absent.

## Storage

Decisions are derived from active goals, learner state, and recent InstructionPlans/Wins. Scheduler metadata is persisted on the new InstructionPlan JSON so historical “why this goal” remains explainable. No scheduler table.

## Learning Trace and next-Win preview

Learning Trace includes a **SCHEDULER** section: selected goal, reason, deferred goals, urgency, starvation flag. Why-not answers:

- Why spelling instead of math (and the reverse)
- Why review instead of new learning (and the reverse)
- Why not the retained terminal skill

Development next-Win preview includes scheduled goal, scheduler reason, planner target skill, mode, and scaffold.

## Device QA (V0.3.8)

A. Goal #1 spelling, #2 math. Generate several Wins. Math must eventually appear.

B. Terminal spelling retained, math still developing. Math becomes the active focus.

C. Sparse weekly user. Review does not dominate.

D. Spelling remediation. Temporary focus, then rotation resumes after recovery.

E. Add a new academic goal. It receives placement soon.

See [device-learning-qa.md](device-learning-qa.md).

## Simulation before / after

Source: `apps/api/eval-results/20260921T155705Z-scheduler-audit.md`. `REVIEW_AFTER_DAYS` still 14.

| Case | V0.3.7 | V0.3.8 |
| --- | --- | --- |
| 21-Win spelling #1 / math #2 | Spelling 21, math 0, starvation | Spelling 16, math 5, no starvation |
| Sparse 24×1 (single academic goal) | 16/24 reviews, ping-pong | 16/24 reviews, **no ping-pong** |
| Age-9 terminal spelling 12×3 | Practice loop on the top leaf | Same leaf in **review/maintenance**, loop gone |

Multi-goal cadence stays about 3:1 spelling:math (`CONSECUTIVE_FOCUS_LIMIT=3`), with max neglect 3. Priority #1 still gets more time.

Sparse-user review **count** did not drop for a single academic goal: after the strand is retained, the only remaining academic work is terminal maintenance/review, so today still has to be a Win. The 16/24 figure was not mandatory intra-strand steal; ping-pong is gone. Spacing was therefore **not** changed.

Once every active academic goal is retained, frequent users also look review-heavy. That is remaining policy uncertainty, not a reason to invent a harder skill.

