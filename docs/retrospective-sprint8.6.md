# Sprint 8.6 Retrospective — Email Quality & Spam Cleanup

**Date**: 2026-03-28
**Duration**: ~1 hour (same session as Sprint 8.5)

## What Was Built

1. **Hero image fix** in `compose_news_digest.py` and `compose_parliament_watch.py` — both now follow the correct two-pass pattern from `compose_monthly_blast.py` (save bytes to BinaryField, re-render with API URL).
2. **Contact form honeypot** — hidden `website` field on frontend, silent reject on backend. Blocks automated spam submissions.
3. **Hard bounce threshold** reduced from 3 to 1 — immediate deactivation on first hard bounce.
4. **Spam cleanup** — deleted 37 bot-injected subscribers with random-string names, deactivated 44 hard-bounced real subscribers identified from Brevo CSV logs.

## What Went Well

- **Root cause analysis via Brevo logs**: The CSV export from Brevo gave us a clear picture of all hard bounces, which led to identifying both the spam bot problem and the dead-email problem in one pass.
- **Pattern recognition**: The hero image bug was caught by comparing the broken commands against the working `compose_monthly_blast.py` — having one correct reference made the fix straightforward.
- **Subscriber hygiene**: Went from 451 to 370 active subscribers by removing spam and dead addresses. Future broadcasts will be more efficient and have better deliverability metrics.

## What Went Wrong

1. **Hero image bytes dumped into email HTML**
   - *Symptom*: Every News Watch email sent on 28 March contained ~2.5 MB of binary data HTML-escaped into `<img src="...">`, producing "Error at line 10:98338 near 'u', Tag 'u' not found".
   - *Root cause*: `generate_hero_image()` returns `bytes | None`, but `compose_news_digest.py` and `compose_parliament_watch.py` assigned it to a variable named `hero_image_url` and passed it directly to the template. The variable name was misleading and no type check caught it. `compose_monthly_blast.py` had the correct pattern but it wasn't applied consistently.
   - *Fix*: Applied the two-pass pattern to both commands. Added `import os` for `BACKEND_URL` lookup. Future: any new compose command should follow the same pattern — save bytes first, render URL second.

2. **37 spam subscribers went undetected for weeks**
   - *Symptom*: Bot-injected subscribers with random-string names (e.g. "sYhogWerLVpOSmdcHIWr") received every broadcast since March.
   - *Root cause*: The subscribe API had no anti-spam measures — any POST to `/api/v1/subscribers/subscribe/` was accepted. No monitoring or validation on subscriber name quality.
   - *Fix*: Added honeypot field to contact form (subscribe form should also be reviewed). Deleted all 37 spam entries. Future: consider adding honeypot or rate limiting to the subscribe endpoint too.

## Design Decisions

- **Deactivate vs delete hard-bounced real subscribers**: Chose deactivation (not deletion) because these are real community members who might re-subscribe with a new email address. Their records serve as audit trail.
- **Delete spam subscribers**: Chose full deletion because these have no value — random names, no source, bot-generated. No audit benefit to keeping them.
- **Bounce threshold = 1**: Dead emails almost never recover. The 3-strike model was overly generous for our use case (small community subscriber list). Brevo already blacklists them server-side anyway.

## Numbers

- Backend tests: 1092 (unchanged)
- Frontend tests: 290 (unchanged)
- Active subscribers: 451 → 370 (37 spam deleted + 44 hard-bounced deactivated)
- Files changed: 4 (2 compose commands, 1 backend view, 1 frontend component)
- Commits: 2
