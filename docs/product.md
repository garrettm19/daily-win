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
