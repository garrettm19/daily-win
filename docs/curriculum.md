# Daily Win — Curriculum

Catalog version: `curriculum_v1`.

Daily Win owns a **small, versioned skill graph**. It is not a thousand-node knowledge map and not a dump of every state standard.

## Hierarchy

```
domain → strand → skill → (optional subskill later)
```

- **Domain:** `MATH`, `READING`, `WRITING`, `GROWTH`, `LIFE`.
- **Strand:** grouping row (`skill_kind=strand`), for example `math.addition`.
- **Skill:** measurable leaf (`skill_kind=skill`), for example `math.addition.within_10`.
- **Subskill:** not used in V0.3. Leave room in the hierarchy; do not invent thousands of leaves.

Growth and life skills remain **separate constructs** with `state_mode=trend`. They are not forced into academic mastery bands or academic standards.

## Skill metadata

Each catalog entry stores:

| Field | Role |
| --- | --- |
| `code` | Stable identity (`math.addition.within_10`) |
| `domain` | MATH / READING / WRITING / GROWTH / LIFE |
| `strand` | Strand slug |
| `parent_code` | Strand code for skills |
| `grade_band_min` / `grade_band_max` | Approximate age years 5–9 |
| `measurable_outcome` | Parent-observable success statement |
| `progression_position` | Order within a strand |
| `state_mode` | `mastery` (academic) or `trend` (growth/life) |
| `taxonomy_version` | `curriculum_v1` |
| `active` | Soft hide without deleting history |

## Academic skills (V0.3)

**Math**

- `math.number_sense.counting`, `math.number_sense.compare`
- `math.addition.within_10`, `math.addition.within_20`, `math.addition.word_problems`
- `math.subtraction.within_10`, `math.subtraction.within_20`
- `math.multiplication.equal_groups`
- `math.fractions.halves_fourths`

**Reading**

- `reading.phonics.letter_sounds`, `reading.phonics.blend_cvc`
- `reading.fluency.smooth_oral`
- `reading.vocabulary.context_clues`
- `reading.comprehension.recall_details`, `reading.comprehension.main_idea`, `reading.comprehension.simple_inference`

**Writing**

- `writing.spelling.high_frequency`
- `writing.sentences.complete_sentence`
- `writing.organization.sequence_events`, `writing.organization.topic_details`

## Growth / life strands

- `growth.persistence`, `growth.independence`, `growth.communication`, `growth.problem_solving`
- `life.money`, `life.organization`, `life.decision_making`

Only persistence currently has a projector and demo feedback mapping.

## Prerequisites

Explicit edges in `domains/learning/prerequisites.py`, seeded to `skill_prerequisites`. Cycle detection runs at seed.

Current edges:

- counting → compare
- counting → addition within 10
- addition within 10 → within 20 → word problems
- addition within 10 → subtraction within 10 → within 20
- addition within 10 → equal groups
- letter sounds → blend CVC → oral fluency
- blend CVC → high-frequency spelling
- recall details → main idea → simple inference
- complete sentence → sequence events → topic details

Rejected (do not add): compare → halves/fourths. Quantity comparison is not equal-share identification.

Planner interpretation:

- Prerequisite **sufficiently evidenced** only if band is `demonstrated` or `retained`.
- Otherwise the planner **reviews the prerequisite** before advancing (`prerequisite_evidence_missing`).
- The LLM never invents canonical prerequisites.

## Assessment probes

Version `assessment_probe_v2`. Each academic Daily Win plan includes a probe:

- `target_skill_code`
- `probe_type` (`observe_independent_try`, `counted_items`, `retell`, `produce_sample`)
- `observable_task`
- `expected_outcome`
- `success_criteria`
- `allowed_support`
- optional `attempt_structure`

The LLM may render wording and mechanics. It may not change the target or success criteria. Application validation currently enforces target skill equality; optional DecisionGateway can check probe fidelity.

## Standards reference layer

Table `skill_standard_refs`. Curated static mappings from Daily Win academic skills to public CCSS identifiers.

- Source/version stored (`CCSS.ELA-Literacy / CCSS.Math`, `2010-public`).
- Standards are **metadata**, not skill identity.
- The LLM is not asked to invent mappings.
- Growth/life skills are **not** mapped.

Do not claim that a Daily Win “covers” a standard in a school-accountability sense. The mapping is a criterion-referenced breadcrumb.

## Versioning

`curriculum_v1` is the catalog identity. Changing hierarchy, prerequisite edges, or standards mapping requires a new `taxonomy_version` / documented curriculum version. Historical plans and evidence keep the version they were stored with.

V0.3.3 repaired prerequisite edges, construct-specific probes, and planner policy inside `curriculum_v1` skill identity. Historical `instruction_plans` keep the policy version they were stored with (`instruction_policy_v1` vs current `instruction_policy_v2`). Do not reinterpret old evidence as if the past had always used the repaired graph.
