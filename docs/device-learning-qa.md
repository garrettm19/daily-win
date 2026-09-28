# Device Learning QA

Development-only. Open **Learning QA** from the Development controls on Home.

Requires a configured synthetic profile (Hayes or custom). Never use real child data.

## Screen contents

- Current synthetic child / engine versions
- Learner snapshot
- Curriculum graph
- Latest Win + reflection status
- Learning Trace (skill, mode, scaffold, implication)
- Why-not explanations
- Likely next decision
- Generate / Reflect / Progress / History / Reset activity history / Restart demo

## Manual scenarios

Expected planner behavior is from `placement_policy_v1` + `instruction_scheduler_v1` + `instruction_policy_v4`. Generate, then open Learning QA.

### SCENARIO A — 9-year-old spelling cold start

Custom profile: age 9, grade 4, goal spelling (+ persistence). No evidence.

**Expected:** first Win is `writing.spelling.multisyllabic_irregular`, mode `diagnostic`, not CVC.

### SCENARIO B — 9-year-old spelling weak diagnostic

After A, reflect academic result **significant help** / incorrect.

**Expected:** next Win steps down one spelling level (endings/suffixes), not kindergarten CVC.

### SCENARIO C — 9-year-old spelling strong diagnostic

After A, reflect **independent**.

**Expected:** does not dump downward. May stay on the same skill to gather a second evidence point. Does not claim mastery. Does not skip to “done” after one probe.

### SCENARIO D — 9-year-old addition cold start

Goal: math addition. No evidence.

**Expected:** `math.addition.word_problems` diagnostic. Not counting objects.

### SCENARIO E — 9-year-old reading cold start

Goal: reading comprehension. No evidence.

**Expected:** `reading.comprehension.simple_inference` diagnostic. Not letter sounds.

### SCENARIO F — older child foundation remediation

Continue weak diagnostics until the planner reaches a foundation skill (for example CVC). Age ≥ 8.

**Expected:** `age_respectful_foundation` is a required renderer contract. Copy must not use baby-talk / “little reader” / kindergarten framing. Academic content may still be foundational.

### SCENARIO G — retained skill review

Build two spaced independent successes on a skill, wait conceptually 14+ days (or inspect Next preview after retained state).

**Expected:** review may appear when due. Review should not dominate every Win.

### SCENARIO H — contradictory evidence

Independent, independent, then incorrect.

**Expected:** learner state does not wildly oscillate. One miss after success is not an automatic remediation trap. Two recent weak sessions after prior independent success can set `needs_remediation`.

### SCENARIO I — goal priority change

After several Wins, edit goals so math becomes #1 (or remove spelling).

**Expected:** historical Wins and evidence remain. Future planner follows the new academic #1. Removed goal does not vanish from History. New goal enters placement if evidence is sparse.

### SCENARIO J — profile interest change

After several Wins, change interests (soccer → space). Do not change goals.

**Expected:** target skill, difficulty, scaffold, and assessment stay on the instructional path. Only engagement framing may change. Learner state is unchanged.

## Reset safety

**Reset activity history** keeps profile/goals; removes Wins, feedback, events, derived state, AI runs, instruction plans.

**Restart demo** removes this tester session’s synthetic setup.

## V0.3.8 scheduling scenarios

### SCENARIO K — Multi-goal spelling then math

Custom profile: spelling #1, math addition #2, persistence overlay.

**Expected:** spelling receives more Wins, but math appears within a handful of generations. Learning QA scheduler section names the selected goal and why the other was deferred. Persistence is an overlay, not the academic slot.

### SCENARIO L — Terminal spelling retained

Build retained state on the top spelling leaf. Keep math developing.

**Expected:** math becomes the active-learning focus. Spelling is maintenance/review, not ordinary repeated practice.

### SCENARIO M — Sparse weekly user

One Win per week over several weeks (or inspect longitudinal/scheduler audit).

**Expected:** reviews are candidates. They must not dominate when active learning still exists. No A/B review ping-pong.

### SCENARIO N — Spelling remediation then recovery

Reflect significant help / incorrect on spelling, then later independent evidence.

**Expected:** spelling may dominate briefly. After recovery, rotation resumes and math receives slots.

### SCENARIO O — New academic goal

After several spelling Wins, add math.

**Expected:** math receives a placement/diagnostic opportunity soon (`new_goal_needs_placement`). Historical evidence is kept.

## V0.4.0 Guide Mode scenarios

### SCENARIO P — New age-9 multi-domain discovery week

Goals: math, writing, reading, persistence. No evidence.

**Expected:** first several Wins rotate first signals across academic domains. One primary objective per Win. CoachProtocol is diagnostic (do not teach first). Copy: getting to know how they learn.

### SCENARIO Q — Very easy math

Independent + automatic / too easy.

**Expected:** challenge can increase later. Not called "too smart".

### SCENARIO R — Writing difficult

Significant help / too hard.

**Expected:** scaffold increases / remediation. Coach card allows a usable next step. One writing target, not every error.

### SCENARIO S — Self-correction

Parent marks self-corrected after an incorrect start.

**Expected:** stored as OBSERVATION. Does not rewrite first-attempt measurement.

### SCENARIO T — Mild frustration, continues

**Expected:** WAIT / ASK cue. Activity continues. No shame copy.

### SCENARIO U — Disengagement

Stopped / avoided.

**Expected:** session can shorten. Dignity preserved. Tomorrow's planner adapts. Not a character failure.

### SCENARIO V — Diagnostic coach card

**Expected:** Your job today says not to teach before the check.

### SCENARIO W — Bonus rated boring twice

**Expected:** future bonus mechanic varies. Academic target unchanged.

### SCENARIO X — End of week Coach Report

After ~5 reflected Wins, Weekly Coach Report matches evidence. No personality labels.

### SCENARIO Y — New week uses last week

**Expected:** scheduler/planner actually use the week's evidence (support, independence, engagement mechanics).

## V0.4.1 latency and pregeneration

### SCENARIO Z1 — First Win then leave

Fresh synthetic profile. Generate the first Win. Complete it. Submit reflection. Leave the app immediately.

**Expected:** reflection succeeds without waiting on Terra. Learning Trace `generated_after_reflection` is true once preparation finishes.

### SCENARIO Z2 — Reopen to READY

Wait, then reopen Home.

**Expected:** today's Win is READY. Opening Home does not call OpenAI (`GET /next-win-state`).

### SCENARIO Z3 — Rapid reopen

Submit reflection. Reopen Home before preparation finishes.

**Expected:** no crash, no duplicate Win, preparing copy, then READY.

### SCENARIO Z4 — Profile change invalidates

Prepare the next Win. Change an active goal or academic baseline field.

**Expected:** prepared Win is invalidated. Old content is not shown as current.

### SCENARIO Z5 — Provider down after reflection

If Terra is unavailable after reflection, today's evidence is kept. Next Home shows a retry path.

## V0.4.2a generation delivery

Learning QA **Generation performance** should show:

- Intent: Background prep / Interactive wait
- Reasoning: medium
- Requested tier: default / fast
- Returned tier: default / priority
- Provider latency

**First-Win timing** also tracks Ready before Guide complete: yes/no when Guide dwell is known (`visible_wait_ms == 0`).

