# SJK(T) Connect — Long-term Roadmap

**Effective**: v2.0.1 (2026-06-26).

This is **high-level direction**, not sprint-level planning. Concrete sprint scope lives in CLAUDE.md's "Next Sprint" section and `docs/implementation-roadmap.md`.

---

## Where we are (v2.0.1)

The platform has reached its first "production maintenance mode" milestone:

- All 528 SJK(T) schools indexed with GPS, leadership, photos, MP context, donation links.
- Public site live at [tamilschool.org](https://tamilschool.org) — trilingual (EN/MS/TA), SEO-friendly URL slugs, Cloud Run + Cloudflare + Supabase stack.
- Parliament Watch pipeline running daily (Hansard download → extract → Gemini analysis → admin-review queue → publish).
- News Watch pipeline running daily (RSS → trafilatura → Gemini triage → school matching via SchoolAlias table).
- Monthly intelligence digest, fortnightly news digest, urgent alerts — all scheduled, all reliable post-Sprint-23/24 hardening.
- Community workflow (suggestions + photo uploads + moderation queue) live.
- Donations via Toyyib Pay live (per-school DuitNow QR + bank details).
- Security baseline: Sprint 29 cleared 103 Python + 28 npm CVEs, broadcast admin views SUPERADMIN-gated, ISR revalidation route token-gated.
- ~519 email subscribers, growing organically.

---

## Direction (12-24 months)

The platform has three layers (intelligence engine + advocacy platform + communications hub). Future work should reinforce all three without trying to redesign any.

### Layer 1 — Intelligence engine

**Goal**: every Tamil-school event of public significance reaches an indexed, searchable, multilingual record within hours of the source.

- **DUN / state-assembly Hansard ingest** — extend the Hansard pipeline beyond Parliament to state-assembly Hansards (where available). Currently we cover MP statements; ADUN statements are uncaptured.
- **Hansard PDF coverage gaps** — backfill historical sittings that parlimen.gov.my added or republished after our initial pull. Periodic reconcile job.
- **Multi-source news fan-out** — beyond Google Alerts RSS, add Tamil-language news sources (Tamil Murasu, Makkal Osai, Tamil Nesan, Hindrant) which currently fall outside our RSS net.
- **Pipeline quality engine evolution** — Sprints 6 + 7 shipped a 4-layer self-correcting engine (Generator → Evaluator → Corrector → Learner). Next: auto-inject Learner-flagged patterns into prompts so the engine improves itself across sprints.
- **Brief quality metric** — quantitative scorecard for AI-generated briefs (sourcing, citation, brevity, urgency-classification accuracy). Currently qualitative.

### Layer 2 — Advocacy platform (public site)

**Goal**: when a parent / journalist / donor / MP / district education officer searches for a Tamil school, our page is the highest-quality result on the first SERP.

- **DUN / constituency page enrichment** — the 2026-06-26 SEO audit found these are the genuinely-thin pages in our "crawled but not indexed" bucket (381 URLs). Future content sprint (deferred per owner pending 2026-07-17 GSC re-pull).
- **MP profile pages** — combine Hansard mentions + scorecard + advocacy contact in a coherent single-page profile per MP.
- **Search ranking improvements** — Sprint 28's URL slug closed the apac.com.my structural gap. Next: inbound links (Wikipedia stubs, district education office directory listings), more page-level depth.
- **Mobile-app-shell PWA** — current site is responsive but not installable. Adding a PWA manifest + service worker would let school admins keep the site as an icon on a phone home screen. Low cost, real UX win.
- **Multilingual content depth** — Tamil and Malay versions of school pages currently inherit English copy patterns. Native-language editorial reviews for the long tail.

### Layer 3 — Communications hub

**Goal**: every school + every subscriber gets the right message at the right time, with zero spam and zero missed urgent alerts.

- **Personalised digest** (deferred from original 2026-05-11 roadmap Sprint 29 slot). Per-subscriber MP personalisation: `Subscriber.home_constituency` FK + per-recipient template injection. Pull in when owner has bandwidth.
- **WhatsApp channel** — outbound parliamentary urgent alerts via WhatsApp. Brevo doesn't offer WhatsApp; Twilio Sender onboarding takes 2–4 weeks. Track from HalaTuju lessons.
- **School-admin-driven broadcasts** — let bound school admins compose their own school-level broadcasts (announcement, donation drive, alumni reunion). Currently admins can only edit static data. Significant feature; sprint-level.
- **Open / click rate dashboards** — Sprint 8.5 added Brevo webhook delivery tracking. Surface the data in admin UI.

---

## Operating model

The platform stays single-developer + AI-assisted. New work runs:

- **Small-change-lane** (per `Settings/_workflows/small-change-lane.md`) for one-line fixes, config tweaks, copy adjustments, urgent SEV3/4 patches. Triggers a Consolidation Review every ~10 entries.
- **Sprints** (per `Settings/_workflows/sprint-start.md` + `sprint-close.md`) for anything ≥6 files, new model/feature/page, or touching money / consent / auth / PII.
- **Major release tags** at coherent narrative milestones (v2.0, v2.0.1, v2.1, v3.0...). Each tag triggers `release.md` (notes + tag + verification). Major version bumps that change operating posture trigger `project-complete.md` (LICENSE/SLA/roadmap review).

External contributors not currently sought; if/when they appear, `CONTRIBUTING.md` documents onboarding.

---

## Non-goals

The following are **explicitly out of scope** for the v2 series:

- **Becoming a parent-facing app for individual school selection.** That's a different product (parent journey, profile, application tracking). HalaTuju is that product.
- **Replacing the schools' own websites or internal CMSes.** SJK(T) Connect aggregates public information; it's not an LMS or a school operations platform.
- **Becoming a paid SaaS for individual schools.** Free-to-school is a core principle. Donations from communities to schools, yes; subscription pricing on schools, no.
- **Government-mandated reporting / official records.** MOE owns those. We aggregate and surface; we don't replace.
- **Real-time push or messaging app.** Email + (future) WhatsApp are the comms channels. No in-app chat.
- **Election prediction / polling.** Electoral context (GE15 results, constituency demographics) is informational; we don't model future elections.

---

## Tech debt direction

- **Stay on Django 5.2 LTS** for the v2 series. Move to Django 6 only when a feature reason emerges OR 5.2 EOL <12 months away (whichever first).
- **Stay on Next.js 16** for the v2 series. Move when a meaningful Next feature lands (probably 17+ or when React 19 stabilises in App Router).
- **Tech debt audit cadence**: at every major version bump OR every 6 months, whichever comes first.
- **Test coverage**: maintain ≥85% for newly-written code. Test-coverage padding sprints (cleaning up TD-12-style 26% files) only when the underlying code is being modified for another reason.

---

## What would trigger v3.0

- Major UI redesign (whole-site refresh, not feature additions).
- Schema migration that breaks backwards compatibility (e.g. UserProfile model restructure that requires re-sign-in).
- New paid/feature tier introduced.
- Open-sourcing decision (if we go fully open-source with external contributors, that warrants a v3.0 tag + governance overhaul).

Otherwise v2.x continues indefinitely with small-change-lane + occasional sprint deliverables.

---

## Review cadence

This roadmap reviewed at every major version bump. Owner can revise without sprint ceremony.

Last reviewed: 2026-06-26 (v2.0.1).
