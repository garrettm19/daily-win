# Local parent pilot — Mason only

This is the only document needed while testing Daily Win with Cory. Current build is a **development/demo system**. Demo-session isolation is not production auth. Until production privacy controls exist, use a **synthetic or minimized/pseudonymous** profile — especially on a public Cloudflare Quick Tunnel. Do not enter a legal child name, school, teacher, address, diagnosis, medical details, photos, school documents, or private family notes. Do not make legal compliance claims.

A READY unused Win remains the current activity until it is reflected, invalidated, or reset. Home still calls that slot **Today’s Win** even if it was prepared on an earlier calendar day. That is intentional: Daily Win does not auto-expire unused READY content.

## Before Cory arrives

1. Start the database: `docker compose up -d db`
2. Start the API: `uv --directory apps/api run uvicorn daily_win_api.main:app --reload --host 0.0.0.0 --port 8000`
3. Start the tunnel or confirm the phone can reach the PC on LAN.
4. If the Cloudflare Quick Tunnel URL changed, update `apps/mobile/.env.local` `EXPO_PUBLIC_API_URL` (no trailing slash) and **restart Metro**. Tunnel restart always changes the URL. V0.4.4 does not add production infrastructure for this.
5. Start Metro: `npm --prefix apps/mobile start`
6. Run `powershell -File scripts/pilot-preflight.ps1`
7. On the phone: enable **Parent Pilot View**, then **Start fresh parent pilot** (same as Restart demo — this tester only; other devices are not affected).
8. Confirm Home shows the first-run product promise, not a leftover Win.

If Mason tested before Cory: always Start fresh parent pilot so Cory gets a genuinely empty session.

## Hand the phone over

Say approximately:

> Use this like you would at home. Don’t worry about testing the app correctly. If something is confusing, do what you’d naturally do. Afterward I’ll ask what worked and what didn’t.

Then: **do not explain the interface.** Do not mention scheduler, learner state, prompt, Terra, or Alpha. Observe. Notes: `docs/parent-pilot-observation.md`. Ratings: `docs/parent-pilot-feedback-template.md`.

## After the session

Five-tap the Daily Win mark (development only) to restore developer surfaces. Inspect Learning QA / Learning Trace. Do not interpret “this UI was confusing” as information about the child.

## Five-day plan

Do not manipulate child results.

| Day | Focus |
| --- | --- |
| 1 | Cold start, Guide, first Win. Watch onboarding comprehension. |
| 2 | Returning READY Win. Was adaptation noticeable? |
| 3 | Another Win; honest weak evidence if that is what happened. Watch support. |
| 4 | Progress without explanation. |
| 5 | Complete a Win, read Weekly Coach Report. Ask: did this save planning work? |
