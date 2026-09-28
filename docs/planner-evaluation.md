# Daily Win — Planner evaluation

Offline, deterministic evaluation of InstructionPlanner, the academic projector, assessment probes, and structural renderer checks. Results are **not** learner memory.

Do not run a large live model evaluation from this document. Terra (`gpt-5.6-terra`) remains the product baseline.

See [educational-quality.md](educational-quality.md) for the curriculum audit, support semantics, Progress claim rules, and remaining risks.

## What is evaluated

Four suites, plus the existing generation harness:

| Suite | `--suite` | Fixtures |
| --- | --- | --- |
| Learner-state projector | `learner` | `eval/learner_cases.py` |
| Instruction planner | `planner` | `eval/planner_cases.py` |
| Assessment probes | `probes` | `eval/probe_quality.py` |
| Renderer / quality | `quality` | theme variants, parent burden, anti-patterns, Progress copy, fake structural render |
| DecisionGateway labels | `decision` | `eval/decision_fixtures.py` (Fake only) |
| Curriculum integrity | `integrity` | `domains/learning/integrity.py` |
| Generation comparison | `--model` / `--sample` | `eval/fixtures.py` + `eval/scoring.py` |

All suites refuse real child data. Synthetic names only (Nova, Hayes, Remy, Pax, Shay).

## Planner golden cases

Each case specifies:

**INPUT:** profile (age 5–9, grade K–4), goals, skill states, recent evidence/themes.

**EXPECTED:** target skill, mode, difficulty, scaffold, reason-code subset, assessment objective.

The planner golden cases evaluate frozen `plan_instruction_v3()`. Current production planning is `instruction_scheduler_v1` + `instruction_policy_v4`. See [instruction-scheduling.md](instruction-scheduling.md).

Coverage:

- Ages 5–9 and grades K–4
- Math, reading, writing, growth overlay, life overlay
- New learning, practice, review, remediation
- Missing prerequisites, retained skills, regression
- Parent-priority conflicts
- Multiple valid next skills (strand order still wins)
- Interest/theme changes that must **not** change the target
- Duration clamp 10–25

Why-not examples:

| Situation | Expected | Must not select |
| --- | --- | --- |
| Goal: addition within 20; within 10 not demonstrated | practice within 10 | within 20 |
| Goal: CVC blending; letter sounds missing | practice letter sounds | blend CVC |
| Goal: writing organization; complete sentence missing | practice complete sentence | sequence / topic details |
| Goal: inference; main idea emerging | practice main idea | simple inference |
| Word problems; within 20 only developing | practice within 20 | word problems |
| Fresh demonstrated within 10 | introduce within 20 | stay on within 10 or jump to word problems |

Interests soccer vs dinosaurs: same instructional target. Theme may change. That is how the suite proves instructional personalization ≠ engagement personalization.

Known current policy (asserted):

- Age does not skip candidates or invent mastery (`age9_addition_missing_counting_is_diagnostic`).
- Fluency waits on CVC blending.
- `emerging` + `needs_remediation` is **remediation**.
- Supporting skills cannot bypass the same prerequisite gate as primary.

## Runner commands

From `apps/api` (or with `uv --directory apps/api`):

```powershell
uv run python -m daily_win_api.eval --suite planner
uv run python -m daily_win_api.eval --suite learner
uv run python -m daily_win_api.eval --suite probes
uv run python -m daily_win_api.eval --suite quality
uv run python -m daily_win_api.eval --suite decision
uv run python -m daily_win_api.eval --suite integrity
uv run python -m daily_win_api.eval --suite all
```

Generation comparison **preparation** (fake by default; Terra is baseline):

```powershell
uv run python -m daily_win_api.eval --model gpt-5.6-terra --sample 5
uv run python -m daily_win_api.eval --model gpt-5.6-luna --sample 5
uv run python -m daily_win_api.eval --model gpt-5.6-sol --sample 5
```

Live spend is opt-in only:

```powershell
uv run python -m daily_win_api.eval --live --model gpt-5.6-terra --sample 5
```

Do not run a large live eval automatically.

## Generation fidelity (structural first)

Given a fixed InstructionPlan, automated checks (before any human score):

- schema pass
- target skill fidelity (draft primary == plan primary)
- assessment fidelity (probe task appears in `observation_focus`)
- duration / materials / LEARN-DO-GROW
- deterministic safety
- parent-burden flags
- anti-pattern flags
- no repeated recent title

Human-scored dimensions stay separate (empty until a reviewer fills them):

Generation rubric in `eval/scoring.py`: age appropriateness, educational usefulness, personalization, parent clarity, coherence, engagement, adaptation, novelty, physical safety, overall usefulness.

Expert-review export in `eval/expert_report.py` uses the educational 1–5 set plus PASS / NEEDS REVISION. Those scores must not be written to PostgreSQL child tables.

Recorded comparison fields when a small live sample is later run: schema pass rate, planner fidelity, assessment fidelity, latency, tokens, estimated cost, human scores. Terra remains baseline.

## Theme vs learning

`theme_variants_keep_instruction()` plans the same writing-organization state three times (soccer / space / animals) and asserts:

- primary skill unchanged
- assessment probe target unchanged
- assessment objective / success criterion unchanged
- engagement theme constraints **do** change

Synthetic renders reuse that plan and only retitle framing.

## Model comparison readiness

Supported ids: `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`.

The harness already records schema validity, instruction-plan alignment, latency, tokens, and estimated USD. Expert/human scores stay empty. DecisionGateway is not enabled on the demo path. No SKU switch is authorized by this eval package.

## DecisionGateway readiness

Labelled Fake accuracy is measured. Confidence calibration is explicitly `None`. Difficulty/scaffold Fake answers are constant True unless a fixture forces them. That is enough to keep the harness honest and **not** enough to turn verification on.

## Version stamps in the suite report

`run_offline_suites()` writes:

- `curriculum_version`
- `instruction_policy_version`
- `projector_version`
- `probe_catalog_version`
- planner case count
- curriculum findings (remaining uncertainty, rejected edges)
- `curriculum_review` (one section per academic skill)

Output lands in `apps/api/eval-results/` (gitignored). Not canonical memory.
