# Daily Win — Educational quality

V0.3.2 asks a different question than V0.3.1. The learner loop is connected. This document asks whether instructional decisions are **actually good**.

This is an **offline evaluation contract**. It does not add product features, taxonomy leaves, Jev, live model spend, peer percentiles, or infrastructure.

Related: [planner-evaluation.md](planner-evaluation.md), [curriculum.md](curriculum.md), [instruction-policy.md](instruction-policy.md), [learner-model.md](learner-model.md), [model-evaluation.md](model-evaluation.md).

## Versions that must not rewrite history silently

| Artifact | Current id | Owner |
| --- | --- | --- |
| Skill graph / standards mapping | `curriculum_v2` | `domains/learning/taxonomy.py`, `prerequisites.py`, `standards.py` |
| Planner policy | `instruction_policy_v4` (frozen fixtures: `v3`) | `domains/learning/planner.py` |
| Instruction scheduler | `instruction_scheduler_v1` | `domains/learning/scheduler.py` |
| Placement policy | `placement_policy_v1` | `domains/learning/placement.py` |
| Academic projector | `academic_projector_v1` | `domains/learning/academic.py` |
| Assessment probe catalog | `assessment_probe_v2` | `domains/learning/probes.py` |
| Prompt renderer | `daily_win_generator_v5` | immutable v1–v4; current renderer v5 |

Future changes to hierarchy, prerequisites, standards mapping, or planner policy require a **new version id**. Historical `instruction_plans`, `learning_events`, and derived snapshots keep the version they were written with. Do not reinterpret old evidence under a new graph as if the past had always meant the new thing.

## Support-level semantics

These meanings are shared across skills. They are parent-facing guidance, not learner truth.

| Result | Parent meaning |
| --- | --- |
| Independent | The child completes the **measured part** without instructional help. A brief wait or encouraging presence is not a prompt. |
| Light prompt | One short cue or question that does not contain the answer. Example: “What happened first?” or “Try counting from one again.” |
| Significant help | Multiple prompts, modelling, a partial answer, rearranging for the child, direct guidance, or step-by-step support. |
| Incorrect | The measured part was attempted and the observable outcome was not met, even after help. |
| Not attempted | The measured part was skipped or not reached. |

Do not invent per-skill support scales. Neatness, enjoyment, and effort are not support levels.

## Curriculum quality audit (`curriculum_v1`)

Audit source: `apps/api/src/daily_win_api/eval/curriculum_audit.py`. It inspects every academic **skill** (20 leaves; not strands, not growth/life). It does **not** expand the taxonomy.

What counts as evidence for every academic skill:

- A parent-reported `academic_result` on a V4 Daily Win whose `AssessmentProbe.target_skill_code` is that skill, and the observable outcome was attempted.

What does **not** count:

- Enjoyment, neatness, effort, time spent, parent guesses about school level, free-text notes, growth/persistence observations, or a result from a Daily Win that had no academic probe.

### Academic skills

V0.3.3 kept all 20 academic leaves and made each one measurable in a short parent activity. No new taxonomy identity. Construct-specific probes are a CI invariant.

The educator-facing export (`eval/expert_report.py` → `curriculum_review_markdown`) is the readable catalog. Offline suite output also writes `*.curriculum-review.md`.

| Code | Prerequisites | Probe status | Standards |
| --- | --- | --- | --- |
| `math.number_sense.counting` | — | construct-specific | K.CC.B.5 |
| `math.number_sense.compare` | counting | construct-specific | K.CC.C.6 |
| `math.addition.within_10` | counting | construct-specific | 1.OA.C.6 |
| `math.addition.within_20` | within 10 | construct-specific | 1.OA.C.6 |
| `math.addition.word_problems` | within 20 | construct-specific; oral “how many in all”, total ≤10 | 1.OA.A.1 |
| `math.subtraction.within_10` | addition within 10 | construct-specific | 1.OA.C.6 |
| `math.subtraction.within_20` | subtraction within 10 | construct-specific | 1.OA.C.6 |
| `math.multiplication.equal_groups` | addition within 10 | construct-specific; 2–3 groups of ≤5, age 8–9 | 3.OA.A.1 |
| `math.fractions.halves_fourths` | none (compare rejected) | construct-specific; identify already-split half and fourth | 1.G.A.3 |
| `reading.phonics.letter_sounds` | — | construct-specific | RF.K.3.A |
| `reading.phonics.blend_cvc` | letter sounds | construct-specific | RF.1.2.B |
| `reading.fluency.smooth_oral` | CVC | construct-specific; one 6–8 word familiar sentence | RF.1.4 |
| `reading.vocabulary.context_clues` | — | construct-specific; one spoken sentence | L.2.4.A |
| `reading.comprehension.recall_details` | — | construct-specific | RL.1.1 |
| `reading.comprehension.main_idea` | recall | construct-specific | RI.1.2 |
| `reading.comprehension.simple_inference` | main idea | construct-specific; 1–2 sentences, age 7–9 | RL.2.1 |
| `writing.spelling.high_frequency` | CVC | construct-specific; one 2–4 letter word | L.1.2.D |
| `writing.sentences.complete_sentence` | — | construct-specific | L.1.1.J |
| `writing.organization.sequence_events` | complete sentence | construct-specific | W.1.3 |
| `writing.organization.topic_details` | sequence events | construct-specific | W.1.2 |

`1.OA.C.6` legitimately spans addition/subtraction within 10 and 20. Related skills, not duplicate identities.

### Prerequisite repairs (V0.3.3)

Accepted edges:

- counting → addition within 10
- addition within 10 → subtraction within 10
- CVC blending → oral fluency
- CVC blending → high-frequency spelling (tighter than letter-sounds → spelling)
- addition within 10 → equal groups

Rejected:

- compare → halves/fourths — comparison of quantities is not the same competency as identifying equal shares of a whole.

Age/grade is a starting prior in `placement_policy_v1`. A 9-year-old with a new addition goal and no evidence gets a **grade-band diagnostic of addition stories**, not a walk to counting and not a fabricated mastery band. See [placement-calibration.md](placement-calibration.md).

## Assessment validity

Each catalog probe is scored by `eval/probe_quality.py`. Every **active** academic skill must pass. Adding a new academic skill without a valid probe fails CI.

A probe is valid only if:

- `target_skill_code` equals the planned skill
- the observable task is construct-specific (not the generic fallback “Invite one independent try at the planned skill.”)
- success criterion is explicit
- the task is reasonable in a Daily Win
- the task/outcome do not measure affect, neatness, or effort

Rejected structurally:

| Target | Bad probe | Why |
| --- | --- | --- |
| Reading comprehension | “Did the child enjoy the story?” | Affect is not comprehension |
| Writing organization | “Did the child write neatly?” | Neatness is not organization |
| Addition within 10 | Probe target set to within 20 | Wrong construct |
| Addition within 10 | “Did the child try hard?” | Effort is not the skill |
| Any skill | Generic independent-try fallback | Does not measure the construct |
| Main idea | Missing success criterion | Success must be explicit |

## Learner-state golden cases

Projector: `academic_projector_v1`. Fixtures in `eval/learner_cases.py`.

| Case | Evidence | Expected |
| --- | --- | --- |
| A1 | incorrect | emerging |
| A2 | incorrect → light prompt | developing |
| A3 | … → one independent | developing (not demonstrated) |
| A4 | … → spaced independent (≥ 7 days) | retained |
| B1 | two independent results, same session | developing; **not** retained |
| B2 | two independent sessions, same calendar day | demonstrated; **not** retained |
| C | retained → later incorrect + significant help | developing + `needs_remediation` |
| D | one independent among later incorrects | developing + remediation; **not** demonstrated/retained |
| — | significant help only | emerging |
| — | not attempted / empty | not_observed |
| — | two independents 6 days apart | demonstrated, not retained |

Policy note: `emerging` plus `needs_remediation` selects **remediation**. Newer contradictory/weak evidence takes precedence over the generic emerging-state branch.

## Parent-facing Progress claims

Every Progress sentence must be traceable to canonical evidence or deterministic derived state.

Allowed shape: “Hayes completed this skill independently in two Daily Win activities.”

Prohibited shape: “Hayes is advanced in writing,” “below grade,” percentiles, mastery, gifted, failed, standardized.

`eval/progress_claims.py` scans current copy. Human eval scores never enter learner tables.

## Parent burden

Promise: briefing ~30–60 seconds, activity ~15–20 minutes (hard clamp 10–25), reflection < 60 seconds.

Structural flags (`eval/renderer_quality.py`):

- more than 4 materials
- more than 10 steps
- coaching > 120 words
- observation/reflection prompt > 40 words
- duration outside 10–25, or longer than the preferred 20-minute ceiling

The fake aligned Hayes draft is inside the promise. Live model outputs are scored the same way when someone later runs `--sample 5`.

## Educational anti-patterns

Structural rejection fixtures:

- worksheet disguised by theme
- answer-giving parent prompts
- excessive parent scripting (`Say: "…"`)
- fake praise (genius / gifted / so smart)
- personality labels
- forced interest stuffing
- too many skills in one activity
- assessment measuring the wrong construct

Planner/learner suites cover the remaining anti-patterns:

- advancement without prerequisite evidence (why-not cases)
- single observation interpreted as mastery (learner cases A3/B)
- instruction target unchanged when only nouns/interests change (theme vs learning)

Noun-only repetition of a recent Win is a renderer check (`no_repeated_recent_theme`) plus DecisionGateway `substantially_repeats_recent_activity`.

## Renderer contracts (V0.3.5)

Blind-review weaknesses that can be checked structurally are now Daily Win rules, not model taste. Source: `domains/daily_wins/renderer_contract.py`. Labelled good/bad fixtures from bakeoff cases 1–8 live in `eval/renderer_contract_cases.py`.

Hard (production reject + retry, `renderer_contract_failed`):

- `three_step_visual` → exactly three parent-visible cues, not a prose description
- diagnostic: canonical probe in LEARN **before** teaching/practice; no second final test
- exactly one canonical academic result source (`observation_focus`); no competing “final challenge/mission/check/test”
- majority of active minutes on the primary academic skill when a growth overlay is present
- review: retrieval/practice plus a distinct independent check, not one thin test item
- itemized skills (facts, CVC, spelling): canonical check item must be extractably distinct from practice when items are present

Soft (eval flags only):

- conservative section-duration heuristics (too thin / too dense)
- disconnected growth overlay (soccer-style second game)
- ambiguous assessment language that does not already fail the canonical-assessment rule

A growth target is an overlay inside academic work, not a separate main activity, unless the InstructionPlan explicitly requires a separate activity. Fresh-item rules are not forced onto qualitative constructs.

v4 is frozen. Current renderer is `daily_win_generator_v5` because these contracts had to be stated to the model, not only rejected after the fact.

## Theme vs learning

Same `InstructionPlan` skill, success criterion, and assessment; only `engagement_theme_constraints` (and rendered framing) may change.

Example: writing organization / sequence events with soccer, space, and animals interests. Instructional objective stays `writing.organization.sequence_events`. This is a core Daily Win invariant: instructional personalization ≠ engagement personalization.

## Difficulty calibration

Not psychometric. Internal consistency labels only:

| Band + scaffold | Label |
| --- | --- |
| not_observed + introduce + high scaffold | appropriate |
| not_observed + diagnostic + medium scaffold | appropriate |
| developing + practice + medium scaffold | appropriate |
| not_observed + independent try | too hard |
| retained + high scaffold (not remediation) | too easy |
| demonstrated + review + medium | appropriate |

## Expert-review export

`eval/expert_report.py` builds a record with:

- profile summary
- learner state
- InstructionPlan
- generated activity
- assessment probe
- planner rationale
- empty 1–5 fields: educational usefulness, target-skill alignment, age appropriateness, scaffold appropriateness, assessment validity, parent clarity, engagement, overall quality
- `PASS` / `NEEDS REVISION` left empty until a human scores

It also exports one section per academic skill for an educator: name, grade band, prerequisites, measurable outcome, probe, success criterion, standards mapping, and planner examples. That markdown is written next to the offline suite JSON.

Human scores are evaluation artifacts only. They are not learner data.

## DecisionGateway eval

DecisionGateway stays **off** in the normal demo. Offline labelled Fake fixtures cover:

- `follows_target_skill`
- `assessment_probe_measures_target`
- `difficulty_matches_plan`
- `scaffold_matches_plan`
- `substantially_repeats_recent_activity` (`repeats_recent`)
- `physical_risk_present`

Metrics: classification accuracy, false accept, false reject, safety false negatives. Confidence calibration is **not** claimed (`None`). Fake always returns True for difficulty/scaffold unless forced — that is a readiness gap, not a reason to enable Jev.

## Peer comparison remains off

Do not implement percentiles. Daily Win history alone is not a norm-referenced instrument.

Later, a percentile would require all of:

1. Validated benchmark items
2. Standard administration
3. A representative norm population
4. Age/grade norms
5. Psychometric calibration
6. Confidence / error estimates

Until those exist, Progress stays within-child and criterion-referenced.

## Remaining educational risks

- Fluency, inference, equal groups, fractions, context clues, spelling, and word problems are **narrowed** constructs, not full school assessments.
- Diagnostic mode shortens the first unobserved check for ages 8–9; it still does not infer skill from age.
- Fake verifier does not inspect draft difficulty/scaffold against the plan.
- Exploratory n=8 Terra vs Luna bakeoff is complete; Terra remains default. Duration plausibility and some growth-overlay integration remain heuristic, not exact timing.
