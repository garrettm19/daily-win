# Daily Win — Placement calibration (V0.3.6)

Policy version: `placement_policy_v1`. Instruction policy: `instruction_policy_v4` (frozen fixtures `instruction_policy_v3`). Scheduler: `instruction_scheduler_v1`. Curriculum identity: `curriculum_v2` (spelling leaf expansion only). Historical `instruction_plans` keep the policy and skill codes they were stored with.

**Core principle:** age/grade provides a starting prior. Daily Win evidence determines actual level. Age never writes mastery.

## Audit of the V0.3.5 no-evidence path

When a 5–9-year-old had a selected academic goal and no Daily Win evidence, `instruction_policy_v2` walked prerequisites recursively. A prerequisite counted as missing unless its band was `demonstrated` or `retained`. `not_observed` was treated the same as “cannot do this.”

That produced activities materially below a reasonable age/grade starting point:

| Age | Goal | Old first plan | Why it was too low |
| --- | --- | --- | --- |
| 9 | Spelling | `reading.phonics.letter_sounds` / CVC sounding-out | `writing.spelling.high_frequency` required CVC blending; blending required letter sounds; all were unknown |
| 9 | Addition | Counting objects | `within_10` required counting; counting was unknown |
| 9 | Reading comprehension | Could fall to phonics when those edges were missing | Unknown prereqs walked to the earliest leaf |
| 9 | Writing organization | Complete-sentence mechanics | Sequencing required a complete sentence; the sentence skill was unknown |
| 5 | Addition | Counting | Same unknown=missing walk, which is closer to a K entry point |

`not_observed` means **we do not know**. It must not imply **the child cannot do this**.

## Unknown vs observed weakness

| State | Meaning | Placement effect |
| --- | --- | --- |
| `not_observed` / no snapshot | Unknown | Do not recurse to the earliest prerequisite. Start near the age/grade entry skill and run a short diagnostic. |
| `emerging` / `developing` / `needs_remediation` | Observed weakness | Prerequisites still gate. Step down one generation-supported academic prerequisite when a diagnostic at the current skill was weak. |

Recursive prerequisite walking remains for **observed** weakness and for advancement after independent evidence. It is not used merely because state is missing.

## Grade-band starting prior

Each academic leaf has placement metadata (`domains/learning/placement.py`):

- reasonable entry age band
- whether it may be an initial diagnostic target
- whether it is primarily a remediation/foundation skill for older learners

Age/grade selects the highest progression skill in the selected strand whose `entry_age_min` is ≤ the child’s age. That choice is **not** stored as learner mastery.

### Starting rules (diagnostic entry, no evidence)

| Strand | Age 5 | Age 7 | Age 9 |
| --- | --- | --- | --- |
| Addition | `within_10` | `within_20` | `word_problems` |
| Subtraction | `within_10` | `within_20` | `within_20` |
| Multiplication | — | — | `equal_groups` |
| Phonics | letter sounds | CVC blending | CVC blending |
| Comprehension | recall | main idea | simple inference |
| Spelling | CVC | patterns | longer/irregular |
| Organization | sequence (age 6+) | sequence | topic details |

## Placement policy (`placement_policy_v1`)

For a learner with insufficient evidence in the selected strand:

1. Start near an age/grade-appropriate skill in that strand.
2. Run a short diagnostic (about 2–4 observable items; not a parent-administered test).
3. Use the structured academic result to remain, move upward later, or step down one level.
4. Descend to foundational prerequisites only when evidence warrants it.

`PlacementPolicy` chooses the diagnostic entry. `InstructionScheduler` chooses the academic goal. `InstructionPlanner` (`instruction_policy_v4`) chooses today’s plan using that placement plus learner state. Age heuristics are not hidden inside the planner’s candidate walk.

Persisted on each new `InstructionPlan`:

- `placement_policy_version`
- `placement_entry_label`
- `placement_why`
- `presentation_constraint` (when an older child is on a foundation skill)

Development view can show: selected goal, expected entry, evidence (none yet vs later diagnostic), placement (Diagnostic vs Foundation review), and why.

## Spelling progression (`curriculum_v2`)

Minimum useful 5–9 sequence. Legacy `writing.spelling.high_frequency` remains in the catalog for historical evidence and is **unsupported for generation**.

| Code | Entry band | Measurable outcome | Probe |
| --- | --- | --- | --- |
| `writing.spelling.cvc` | K–1 / ages 5–6 | Spell one CVC word (cat, sun, map) | Dictation of one CVC word |
| `writing.spelling.patterns` | Grade 1–2 / ages 6–8 | Spell one common pattern word (rain, boat) | Dictation of one pattern word |
| `writing.spelling.endings_suffixes` | Grade 3 / ages 8–9 | Spell one inflected word (jumped, playing) | Dictation of one `-ed`/`-ing`/`-s` word |
| `writing.spelling.multisyllabic_irregular` | Grade 3–4 / age 9 | Spell one irregular or longer word (because, friend) | Dictation of one longer/irregular word |

Prerequisites: CVC blending → CVC spelling → patterns → endings → longer/irregular. Those edges still control remediation and advancement. They do not force a 9-year-old with no evidence to start at CVC.

A 9-year-old spelling diagnostic samples around the expected level (pattern, suffix, irregular/longer, easier anchor). It is not a psychometric battery and does not report percentiles.

## Diagnostic result logic

Parent results already supported: `correct_independently`, `correct_after_light_prompt`, `correct_after_significant_help`, `incorrect`, `not_attempted`. Optional `correct_count` / `attempted_count` remain available when the probe uses 2–4 items.

Conservative deterministic rules (no behind/ahead labels):

- Independent success → remain and gather more evidence (`developing` after one success is not mastery).
- Significant help / incorrect / emerging with no independent success → step down one level (`foundation_review`).
- Do not walk all the way to kindergarten because a single diagnostic was weak.

## Age-respectful foundation presentation

If an older child (age ≥ 8) genuinely needs a foundation skill (CVC spelling, letter sounds, counting), the activity keeps the same construct and uses older presentation/context. Kindergarten-style baby language is a renderer/eval hard contract: `age_respectful_foundation`. Prompt v5 is unchanged; the contract is application-enforced.

## Educational review

Grade-level standards (CCSS ELA/Math mappings already on each leaf) are **reference metadata** for a reasonable diagnostic starting point. They are not proof that this child has mastered the skill. Daily Win evidence establishes the learner’s actual state. Age never fabricates a `demonstrated` or `retained` band.

## Existing learner safety

New placement logic applies to **new** plans only. Historical instruction plans, events, and derived snapshots are not rewritten. Unknown states are not inferred retroactively.

## Remaining uncertainty

- Four spelling leaves are still a coarse 5–9 model; they are not a full orthography scope and sequence.
- Diagnostic overlays sample a small range around the entry skill; they are not item-response calibrated.
- Cross-strand prerequisites (CVC blending → CVC spelling) still matter after weakness is observed; first-session diagnostics may not mention them.
- Oral fluency, inference, equal groups, and word problems remain short parent-observable probes, not school assessments.
