# Daily Win — Product

## Original vision

Daily Win helps parents intentionally develop their children through short, personalized activities.

The product is **parent-operated**. AI is a **copilot for the parent**, not a companion, tutor, or entertainment surface for the child.

The original behavior comes from a real workflow:

1. A parent gives AI information about their child.
2. AI creates a short personalized Daily Win.
3. The parent and child complete it together.
4. The parent reports what happened.
5. That feedback changes what the system understands about the child.
6. Future Daily Wins adapt accordingly.

A Daily Win is not limited to homework. It may combine:

- academics
- real-world activities
- physical challenges
- persistence
- independence
- problem solving
- communication
- practical/life skills

The activity is designed for the parent and child to do **together**, then continue **offline**. The system’s job is to brief the parent, remember what happened, and improve the next suggestion.

## Target user

**Parents and guardians of elementary-age children**, initially approximately **ages 5–9**.

The primary operator of the app is the parent or caregiver. The child is the learner the system is helping the parent develop. Multiple caregivers in a household must be able to participate over time.

## Core loop

1. **Parent onboarding** — the household and caregivers are established.
2. **Child baseline and goals** — the parent provides starting information about the child.
3. **Personalized Daily Win** — the system proposes a short activity for this child, now.
4. **Short parent coaching briefing** — the parent receives enough coaching to run the activity well.
5. **Parent + child perform the activity offline** — the tablet is not the activity.
6. **Parent submits feedback** — what happened, how it went, what was observed.
7. **Feedback becomes structured evidence** — observations are stored as canonical events, not chat residue.
8. **Learner state updates** — derived understanding of the child is rebuilt from evidence.
9. **Next Daily Win adapts** — the following activity reflects what the parent reported.

## V0.1 demo

The first demo has one job, and it must be unmistakable:

**Parent feedback changes the system's understanding of the child and visibly affects the next Daily Win.**

If a reviewer cannot see that the child’s stored understanding changed, and cannot see that the next Daily Win is different because of that change, the demo has failed—even if generation, UI, or coaching look polished.

The demo gives each development installation an isolated synthetic session. Mason resetting does not affect Cory. **Real child personal information must not be used in the public-tunnel demo.**

## V0.2 demo (development)

**DEMO IMPLEMENTATION.** This is still a development demo on `X-Demo-Session` isolation. That header is **not authentication** and must not exist in production.

A tester can:

1. **First Run** — choose the Hayes preset or create a synthetic demo profile.
2. **Parent Setup** — about 2–3 minutes of made-up developmental context (no real-child PII fields).
3. **Daily Win** — generate a personalized activity from the latest baseline and goals.
4. **Reflection** — parent reports what happened.
5. **Evidence** — application code writes canonical learning events.
6. **Adaptation** — the next Win uses rebuilt learner state.
7. **Progress** — a cautious, evidence-based parent view (no fake scores).
8. **History** — recent Daily Wins, newest first; past reflected Wins are read-only.

Hayes remains the one-tap path. Custom synthetic profiles use the same ContextBuilder. Profile edits insert a new latest baseline and reorder/deactivate goals; they never rewrite old Wins or events.

### Production requirements (not implemented)

Production still requires authenticated household membership, RLS, real-child data minimization review, deletion workflows, and the rest of the security roadmap. Do not treat demo-session isolation as those controls.

## V0.3 learner engine (backend)

The LLM still renders the activity. Daily Win decides **what to teach, how hard, how much scaffold, and what to observe**. See [learner-model.md](learner-model.md) and [ai-architecture.md](ai-architecture.md).

Do not add production auth, AWS, billing, real-child data, peer percentiles, deep knowledge tracing, or a general-purpose agent loop in this phase.

## V0.3.1 academic loop (mobile demo)

A V4 Daily Win now shows a parent-facing check, reflection can submit `academic_result`, and Progress/Insight show cautious academic state separately from growth. InstructionPlanner remains the instructional owner. Decision verification stays off in the normal demo.

Do not add production auth, AWS, billing, real-child data, peer percentiles, or a general-purpose agent loop in this phase.

## V0.3.2 educational quality (offline eval)

The academic loop is connected. V0.3.2 does **not** add product features. It asks whether instructional decisions are actually good: curriculum audit, planner golden cases, probe validity, learner-state edges, parent burden, and anti-patterns. See [educational-quality.md](educational-quality.md) and [planner-evaluation.md](planner-evaluation.md).

DecisionGateway stays off in the normal demo. Peer percentiles stay off.

## Explicit non-goals

Daily Win is **not**:

- an unrestricted chatbot for children
- an AI tutor that replaces the parent
- a product where the child is simply handed a tablet
- a homework mill or worksheet generator
- a surveillance or scoring product that ranks children against each other
- a system whose “memory” of a child lives in LLM conversation history
- a child-facing open-ended AI companion

V0.1 is also **not** trying to prove:

- full multi-child household management polish
- provider-grade model routing or multi-model ensembles
- social features, school integrations, or marketplace content
- autonomous child accounts or child-operated chat
- scale infrastructure beyond a modular monolith and PostgreSQL

## V0.4.0 Guide Mode

The parent becomes the Guide. Daily Win owns learning intelligence (scheduler, planner, CoachProtocol, weekly synthesis). See `docs/guide-mode.md`, `docs/coach-protocol.md`, and `docs/weekly-learning-loop.md`.

## V0.4.1 returning-parent latency

A returning parent should open Home to a READY Daily Win. Reflection must not wait on Terra. The next Win is prepared after reflection, off the UI path. See `docs/generation-latency.md`.

## V0.4.2 first-Win latency

The first Daily Win starts as soon as profile setup is committed. The parent can skip a short Guide intro while Terra runs. Home shows today's focus and the coach card if the Win is still generating. Do not pad onboarding to hide model time. Terra reasoning stays medium. Background prep uses the Standard service tier; only an explicit parent-waiting fallback may request Fast mode. See `docs/first-win-latency.md`.

## V0.4.3 product polish

The V0.4.x loop should feel like one 20-minute coaching product. Parent UI uses a frozen vocabulary (Daily Win, Today’s focus, Your job today, What to check, Reflection, What we learned, What changes next, Progress, Weekly Coach Report). Guide Mode stays four short skippable screens. Educational policy, curriculum, scheduler, and Terra are unchanged. See `docs/product-polish-audit.md` and `docs/product-polish-qa.md`.

