# Product polish audit — V0.4.3

Audit of production-facing screens after the V0.4.3 polish pass. Developer screens are listed separately. Findings are classified HIGH / MEDIUM / LOW. HIGH and clear MEDIUM issues were fixed in this pass. Screens that already worked were not redesigned.

Frozen vocabulary: Daily Win, Today’s focus, Your job today, Challenge, What to check, Reflection, What we learned, What changes next, Progress, Weekly Coach Report, Win of the Week.

---

## Production screens

### First launch

| | |
| --- | --- |
| Purpose | Explain the product and choose Hayes or a custom profile |
| Primary CTA | Start with Hayes |
| Secondary CTA | Create a profile |
| Hierarchy | Name → 20-minute promise → why → actions → quiet demo note |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Opening copy could read like a demo picker, not a product promise | Lead with “20 minutes. One challenge. Know exactly how to coach it.” |
| MEDIUM | “Try the Hayes demo” / “Create a demo profile” over-emphasized demo | “Start with Hayes” / “Create a profile”; demo constraint stays as caption |
| LOW | Dad-forward positioning could exclude other caregivers | Kept parent-neutral “you”; landing line is “Built for parents who want to be more intentional with 20 minutes.” |

### Custom setup

| | |
| --- | --- |
| Purpose | Collect a fictional profile quickly |
| Primary CTA | Next / Create profile |
| Secondary CTA | Back |
| Hierarchy | Step progress → one question group → continue |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Strengths / difficulties sounded diagnostic | “Things that feel easier / harder” |
| MEDIUM | Goal #1 looked exclusive; duration looked like a stopwatch | Rotation helper copy; “About N min — not a stopwatch” |
| MEDIUM | Retry used developer wording | Try again |
| LOW | Five steps remain visually busy | Left schema fields; reduced labels only |

### Guide

| | |
| --- | --- |
| Purpose | Teach Guide Mode in ~30–60 seconds while first Win may generate |
| Primary CTA | Continue / See today’s Win |
| Secondary CTA | Skip intro |
| Hierarchy | Progress → one idea → one body → continue |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Risk of filler screens hiding Terra latency | Four short screens: plan, don’t rescue, hard is okay, report what happened |
| MEDIUM | Skip label was generic | Skip intro |

### Home — first-Win preparing

| | |
| --- | --- |
| Purpose | Show known plan while today’s challenge is prepared |
| Primary CTA | None (wait / leave) |
| Secondary CTA | Profile / Progress / History / Week |
| Hierarchy | Today’s focus → Your job today → Preparing today’s challenge… |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Technical generation stages leaked | One line: “Preparing today's challenge...” |
| MEDIUM | Duplicate “Today’s focus” above the card | Single card eyebrow: Today’s Win |
| LOW | Could feel like a spinner screen | Known focus and job stay visible; parent can leave |

### Home — READY

| | |
| --- | --- |
| Purpose | Answer what we are doing today and start |
| Primary CTA | Start Daily Win |
| Secondary CTA | Quiet nav |
| Hierarchy | Title → skill · ~20 min → what changed → start |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | “View Daily Win” / “Generate today’s Daily Win” felt like a developer console | Start Daily Win / Create today's Win |
| MEDIUM | READY card buried the reason for today | What changed today on the card when present |
| MEDIUM | Invalidated Win could flash as still ready | Invalidated status wins over unreflected payload |

### Home — reflected / next Win

| | |
| --- | --- |
| Purpose | Confirm save and that tomorrow is handled |
| Primary CTA | None required |
| Secondary CTA | View completed Win |
| Hierarchy | Completed Win → Saved. Daily Win is preparing the next challenge. |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Generate CTA after reflection asked another decision | Removed; tomorrow is prepared off-path |
| MEDIUM | Copy implied the parent should wait | “You can close the app.” |

### Daily Win

| | |
| --- | --- |
| Purpose | Coach one 20-minute challenge |
| Primary CTA | Start Daily Win, then Save a reflection |
| Secondary CTA | If needed |
| Hierarchy | Title / time → Your job today → materials → start → LEARN / DO → What to check → GROW → optional bonus |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Full briefing before the first action caused scroll fatigue | Start first; extra coaching behind If needed |
| HIGH | Bonus mentioned mastery; What to check could get lost | Bonus optional 3–5 min; What to check is its own band after DO |
| MEDIUM | LEARN / DO / GROW looked like three equal cards | Academic segments first; GROW quieter |
| MEDIUM | Materials were a prose sentence; empty briefing headers | Bullet list or “Just paper and a pencil.”; hide empty blocks |
| MEDIUM | Discovery Week on one academic goal felt like an exam | Hidden unless two or more domains |
| LOW | Guide-onboarding repeated Guide screens | Removed from the Win body |

### Reflection

| | |
| --- | --- |
| Purpose | Report what happened in under a minute |
| Primary CTA | Save reflection |
| Secondary CTA | Cancel |
| Hierarchy | Feel → check → stuck → notice → finish → optional note |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Snake_case labels; engagement asked every day | optionLabel(); engagement only if too easy/hard or bonus |
| MEDIUM | Too many chips and questions | Cap notice chips at 5; keep academic/setback conditional |
| MEDIUM | Submit copy and failure recovery | Save reflection; answers stay on failure; double-submit lock kept |

### Insight

| | |
| --- | --- |
| Purpose | Show what Daily Win learned and what changes next |
| Primary CTA | Back to Home |
| Secondary CTA | None |
| Hierarchy | Saved. → What we learned → What changes next |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | “The app listened.” felt cute and unspecific | Saved. |
| MEDIUM | Duplicate growth card even when empty / identical | Render only visible, distinct observations |

### Progress

| | |
| --- | --- |
| Purpose | A calm picture of academic and growth skills |
| Primary CTA | None |
| Secondary CTA | Recent Daily Wins |
| Hierarchy | Academic (active first) → growth → recent observations |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Read like a gradebook with evidence jargon | Skill, band, Latest, session count |
| MEDIUM | Long lists and clinical state guide | Other skills we’ve seen collapsed; one trust line |
| MEDIUM | Load error sounded generic | Couldn't load Progress. Your Daily Wins are safe. |

### Weekly Coach Report

| | |
| --- | --- |
| Purpose | Replace a paper weekly summary |
| Primary CTA | None |
| Secondary CTA | None |
| Hierarchy | This week → strong / still work / challenge / enjoyed / next / one thing / Win of the Week |

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Empty section cards and ISO week range | Hide empty lists; 1–2 bullets; human week range |
| MEDIUM | Sparse weeks overclaimed | “Still gathering…” / “Only one Win…” |
| LOW | Win of the Week not selectable | Left as candidates; see future findings |

### History

| | |
| --- | --- |
| Purpose | What we did, when, focus, whether reflected |
| Primary CTA | Open a past Win (read-only) |
| Secondary CTA | None |
| Hierarchy | Simple cards |

| Severity | Finding | Resolution |
| --- | --- | --- |
| MEDIUM | Raw locale dates; empty title was a sentence dump | Today / Yesterday / Sep 21; empty explains next action |
| LOW | “Completed” vs reflection | Reflection saved / pending |

### Profile / edit

| | |
| --- | --- |
| Purpose | Quiet context for engagement and scheduling |
| Primary CTA | Edit profile / Save |
| Secondary CTA | None |
| Hierarchy | About → interests → easier/harder → goals → what works |

| Severity | Finding | Resolution |
| --- | --- | --- |
| MEDIUM | Numeric priority looked exclusive | #1 Main focus / rotation helper |
| MEDIUM | Strengths/difficulties language | Feel easier / harder |
| LOW | Constant editing encouragement | One quiet helper; no extra CTAs |

### Loading / error / empty / success

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | Generic spinners and raw error codes | Short titles; parent errors; codes DEV-only |
| MEDIUM | Offline looked like data loss | Can't reach Daily Win right now. Check the connection and try again. |
| MEDIUM | False empty Home during GET reload | Last known content kept; poll only while generating |
| LOW | Celebratory success | Saved. Tomorrow is being prepared. |

---

## DEV-only screens

### Learning QA / Learning Trace / Development controls

Inspected separately. Production users do not see DemoControls, tester fingerprint, model names, policy versions, or reset actions (`__DEV__` gate). Learning QA and Test feedback are hidden from production navigation (`href: null`). Learning QA groups ENGINE / GENERATION / LEARNER STATE / SCHEDULER / PLANNER / COACH PROTOCOL / EVIDENCE, collapsed by default except ENGINE.

Reset copy distinguishes:

- Reset activity history — Wins, reflections, and learned state go; profile stays
- Restart demo from beginning — this tester session is erased

---

## Visual system

Existing tokens kept (`#FAF8F3`, `#2E6F62`, Nunito headings, system body). Card/button/chip systems were not replaced. Selected chips already use a checkmark plus border, not color alone. Touch targets on chips/nav remain ≥44. Motion: READY/Insight stay small; Reduce Motion still skips Daily Win enter translate. No per-chip haptics. Sparse success haptic on reflection save and READY transition.
