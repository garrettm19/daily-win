# Daily Win — Model evaluation

Terra (`gpt-5.6-terra`) remains the product default until evaluation evidence supports a change. Do not switch models because a cheaper or more capable SKU exists.

## Current recommendation

Keep `OPENAI_MODEL=gpt-5.6-terra`.

A cheaper model (for example `gpt-5.6-luna`) may replace Terra only if a recorded eval shows:

- zero schema failures
- zero accepted deterministic safety failures
- no meaningful regression in personalization or adaptation
- acceptable latency
- human quality close to or equal to Terra
- materially lower cost

Do not select on token price alone. Do not introduce GPT-6 / Sol merely because they are more capable.

## Harness

Synthetic fixtures live in `apps/api/src/daily_win_api/eval/fixtures.py` (Hayes plus other synthetic children, including Nova/Milo/Riley first-Win contexts). They vary age (5–9), interests, academic strengths, primary goals, persistence signals, first vs adaptive Wins, and low/medium/high support. **Do not load real child data.**

Automated checks (see `eval/scoring.py`):

- schema validity
- **instruction-plan alignment** (primary skill must match the plan)
- valid skill codes
- material allowlist
- duration
- LEARN / DO / GROW structure
- deterministic safety
- `adaptation_summary` when the fixture is adaptive
- no caregiver assumption unless that term appears in supplied context
- no inferred pronouns
- no repeated recent title
- bounded context size
- latency, token usage, estimated cost (comparison estimates only)

Three **separate** eval surfaces — do not score only the final prose:

1. **Learner model** — did evidence produce the correct derived band/trend? (`tests/test_learner_engine.py`, `tests/test_longitudinal_nova.py`)
2. **Instruction planner** — did code choose the correct skill/difficulty/scaffold/reason codes? (same tests plus planner unit tests)
3. **Activity renderer / verifier** — did the model follow the plan, and did DecisionGateway atomic questions match labels? (`eval/scoring.py`, `eval/decision_fixtures.py`)

DecisionGateway harness metrics (offline Fake only; **no live Jev**): classification accuracy, false-safe rate, false-reject rate, safety false negatives (weighted more severely), plus placeholders for confidence calibration, latency, and cost.

Human rubric (1–5), stored empty for later scoring:

- age appropriateness
- educational usefulness
- personalization
- clarity for parent
- activity coherence
- fun / engagement
- adaptation quality
- novelty
- physical safety
- overall usefulness

Results write to `apps/api/eval-results/` (gitignored). They are **not** canonical learner data and must not be inserted into child tables.

## Commands

Default is a **small fake-gateway sample**. It does not call OpenAI:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --sample 2
```

List fixtures:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --list
```

Intentional live spend (small sample only):

```powershell
uv --directory apps/api run python -m daily_win_api.eval --live --sample 2 --model gpt-5.6-terra
```

Comparable live SKUs: `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`.

Educational-quality suites (offline, no model call):

```powershell
uv --directory apps/api run python -m daily_win_api.eval --suite all
uv --directory apps/api run python -m daily_win_api.eval --suite planner
```

Prepared comparison commands (still fake unless `--live` is passed). Terra remains baseline:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --model gpt-5.6-terra --sample 5
uv --directory apps/api run python -m daily_win_api.eval --model gpt-5.6-luna --sample 5
uv --directory apps/api run python -m daily_win_api.eval --model gpt-5.6-sol --sample 5
```

V0.3.4 small live renderer bakeoff (identical frozen InstructionPlans; 8 cases × 2 models). Does **not** change `OPENAI_MODEL`:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --compare terra-luna
uv --directory apps/api run python -m daily_win_api.eval --compare terra-luna --live
```

Writes `apps/api/eval-results/<timestamp>-terra-luna.json`, a blinded `-terra-luna-review.md`, and a separate `-terra-luna-reveal.json`. Human scores stay in the review artifact and are not learner data.

V0.3.4a calibration (no live calls). Re-score stored drafts after safety/pricing repairs:

```powershell
uv --directory apps/api run python -m daily_win_api.eval --rescore-bakeoff
uv --directory apps/api run python -m daily_win_api.eval --summarize-review apps/api/eval-results/20260919T211946Z-terra-luna-v034a-review.md --reveal apps/api/eval-results/20260919T211946Z-terra-luna-reveal.json
```

Eval cost estimates use `eval/pricing.py` (operational metadata; last verified 2026-09-19): Terra $2 / $12 per 1M in/out, Luna $0.20 / $1.20. Hard-failure attribution distinguishes model output from application-validator false positives. Production still rejects whatever the current safety validator rejects.

Keep `OPENAI_MODEL=gpt-5.6-terra`. Do not implement routing.

## V0.3.4 human blind review (exploratory)

Terra remains the production default.

An exploratory n=8 blinded pairing (calibrated v0.3.4a review artifact) showed:

- Terra overall **4.75 / 5**, won **7 / 8** model-level pairings
- Luna overall **4.125 / 5**, won **1 / 8**

Terra was stronger on educational quality, plan fidelity, engagement, and assessment quality in this sample. This is **not** a claim of statistical significance. Luna remains a future cost-optimized candidate. Do not implement fallback or routing yet.

See [planner-evaluation.md](planner-evaluation.md) and [educational-quality.md](educational-quality.md). Expert-review scores are evaluation artifacts only.

Do not run a large live evaluation automatically.
