# Guide Mode (V0.4.0)

Daily Win decides the learning. The model creates the experience. The parent provides the human relationship.

The adult is **the Guide**: high standards and high support, not high pressure / low support, and not high comfort / low expectations.

Backend language stays caregiver-neutral (`parent` / `guide`). Product copy may experiment with Dad-forward positioning such as:

- "20 minutes. One challenge. Know exactly how to coach it."
- "Daily Win gives you the plan. You bring the relationship."

If a caregiver role is collected later, UI may say Dad / Mom / Guardian / Other only when the user selected it. Do not encode gender stereotypes in learner architecture.

## Layering

```
InstructionScheduler
  → InstructionPlanner
    → InstructionPlan
      → CoachProtocol (coach_protocol_v1)
        → renderer
          → parent + child activity
            → smart reflection
              → canonical evidence
                → learner state
                  → weekly synthesis
```

| Layer | Owns |
| --- | --- |
| Scheduler | Which academic goal gets today's slot |
| Planner | Exact skill, mode, scaffold, assessment |
| CoachProtocol | How the adult should behave |
| Renderer / Terra | Engaging experience and natural phrasing |
| WeeklyLearningSummary | What the week's evidence actually showed |

Terra may phrase coach cues and project framing. Terra may **not** decide what the child knows, coaching philosophy, learner state, academic target, support level, or weekly factual claims.

## Session shape

Flexible, not mandatory headings:

1. Launch (30–60 sec)
2. Core challenge (primary academic learning)
3. Apply / explain
4. Growth moment (overlay)
5. Reflection (under about one minute)

Default duration remains 10–25 minutes. Optional ~5-minute Bonus Challenge is not academic mastery.

## Discovery week

For a newly configured learner with multiple academic goals, the first several Wins gather a first signal across domains. Copy:

**This week: getting to know how they learn**

Not: testing, assessment battery, placement exam.

Progress is qualitative ("first signal collected" / "still to explore"), not percentages.

## Parent onboarding (about a minute)

1. Don't rescue too fast
2. Ask before telling
3. One skill at a time
4. Hard is okay
5. Support is always available
6. Report what actually happened

## Design inspiration (not claims)

We borrow general principles: personalized level, mastery orientation, adults as guides, high standards + high support, meaningful challenge, life-skill practice, learner ownership.

Daily Win is not an equivalent-outcome product of any other school. Do not use other organizations' performance branding, multiplier claims, or ranking slogans.

## Privacy

Do not seed fixtures or the public-tunnel demo with real children's handwritten packets, report cards, or school records. Synthetic examples only.
