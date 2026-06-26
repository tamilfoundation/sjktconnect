# Contributing to SJK(T) Connect

Welcome! SJK(T) Connect is a public-interest intelligence + advocacy platform for Malaysia's 528 Tamil-medium primary schools. It's run by a single developer (admin@tamilfoundation.org) under the Tamil Foundation banner, AI-assisted, free for schools to use.

Contributions are welcome but small-and-focused over large-and-speculative. If your change is more than a one-line fix, please **open an issue first** so we can scope it together.

---

## Code of conduct

Be respectful. The schools we serve are public institutions teaching children; respect that posture in tone and topic. No partisan editorialising in code, copy, prompts, or PRs.

If you observe behaviour at odds with this in any project surface (issues, PRs, broadcast content), email admin@tamilfoundation.org.

---

## Before you start

1. **Open an issue describing your change.** Even a 30-second issue is enough to confirm scope + that we're not already working on the same thing. Saves both sides time.
2. **Check the roadmap.** `docs/roadmap.md` lists what's in scope for v2.x. Out-of-scope items (parent-facing apps, paid features, real-time messaging) won't be merged.
3. **Check existing work.** `CHANGELOG.md` + `docs/retrospective-sprint*.md` show recent direction. `docs/decisions.md` documents settled architectural choices.

---

## Dev environment setup

See `README.md` under "Local setup". You'll need:

- Python 3.13+ (3.13 is what prod runs)
- Node.js 20+ (16.x line)
- A Supabase free-tier project (database + storage), OR sqlite for local-only testing
- A Google AI Studio API key (Gemini) — free tier is sufficient
- Optional: Brevo API key for email testing
- Optional: Google Maps API key for frontend map

---

## Running the suites

**Don't skip this**. Tests are the contract.

```bash
# Backend (1436 tests)
cd backend
pytest -q

# Frontend (367 tests)
cd frontend
npm test

# Lint
cd backend && ruff check .
cd frontend && npm run lint

# Type-check (frontend)
cd frontend && npx tsc --noEmit
```

If your change touches code, **add or update tests** as part of the same PR. If your change fixes a bug, add a regression test that would have caught it.

---

## Conventions

### Backend (Django + DRF)

- **Models live in `<app>/models.py`**. Cross-app imports OK; avoid circular dependencies.
- **API views** in `<app>/api/views.py` and `<app>/api/serializers.py`. URLs in `<app>/api/urls.py`.
- **Services** (multi-step business logic that's testable in isolation) in `<app>/services/`. Example: `schools/services/revalidation.py`, `broadcasts/services/sender.py`.
- **Management commands** in `<app>/management/commands/`. One-off commands (single-use cleanup, post-incident repair) should be deleted after they run — see `docs/lessons.md` Sprint 28.1 entry. If a command is repeatable, name it intent-first (`relabel_*`, `cleanup_*`, `backfill_*`) — names matching the workspace `.gitignore` patterns (`fix_*`, `debug_*`, `temp_*`) get silently dropped by git.
- **Migrations**: backfill migrations MUST print before / changed / unchanged counts. Silent migrations hide bugs (the "+0 changed but no error" failure mode). RunPython migrations must have `reverse_code` defined where data-modifying.
- **Settings**: `sjktconnect/settings/{base,development,production}.py` — child modules must MUTATE the base dicts (`STORAGES["staticfiles"] = ...`), never REASSIGN (`STORAGES = {...}` silently wipes the base). Generalises to any composite setting.
- **DRF auth**: `DEFAULT_AUTHENTICATION_CLASSES` is pinned to `SessionAuthentication`. Don't add `TokenAuthentication` without CSRF compensating controls.

### Frontend (Next.js 16 + Tailwind + next-intl)

- **Pages live in `app/[locale]/`**. Trilingual (en, ms, ta). New pages need `setRequestLocale(locale)` AND a `messages/{locale}.json` entry for any new string.
- **Components**: stateless functional. Shared components in `components/`; page-local components inline.
- **API client**: `lib/api.ts` is the only place that knows the backend exists. All `fetch()` calls live there.
- **Tests**: `__tests__/` mirrors the source tree. Use React Testing Library + Jest. Mock module-level singletons (`useSession`, `useRouter`) per test file's beforeEach.
- **Tailwind**: use the project's existing `primary-*` purple scale; don't introduce ad-hoc colour values. Visual reference: any existing card component (white bg + rounded-lg + border-gray-200 + 1px-wide x 20px-tall primary-600 accent bar).
- **i18n**: every user-facing string in `messages/`. No bare English string in JSX. Use `useTranslations('namespace')` or `getTranslations('namespace')` (server).
- **NEXT_PUBLIC_* env vars** are baked into the JS bundle at build. Changing them at runtime has no effect on the client bundle.

### Commits + PRs

- **Conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `ops:`. Pick the most accurate prefix.
- **Co-author trailer**: if AI assisted, include `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` (or equivalent for the model used).
- **One logical change per commit**. Don't bundle a bug fix with a refactor with a new feature.
- **Push to a feature branch + open a PR**. PRs against `main` directly are not merged.
- **PR description**: what + why + how to test. Reference the issue.
- **Squash-merge** is the default. Avoid merge commits.

### What does NOT belong in commits

- **Secrets**. Period. Local `.env` is gitignored — keep it that way. Production secrets live in Cloud Run env vars only.
- **Generated files** that aren't reproducibly generated (don't check in build artifacts).
- **node_modules / venv / __pycache__** — already gitignored.
- **Personal email addresses, phone numbers, addresses** of contacts — these belong in env vars or DB rows, not source.

---

## Sprint-driven work

Substantive features run via the workspace WAT framework. Workflows live at `Settings/_workflows/`. If you're adding a multi-step feature:

1. `sprint-start.md` — read recent lessons + decisions, define scope, confirm with owner.
2. Code + test + document.
3. `sprint-close.md` — CHANGELOG line + retrospective + push.

If you're shipping a one-line fix:

1. `small-change-lane.md` — classify as small, run, log to `docs/consolidation-log.md`.

If you're tagging a release:

1. `release.md` — generate notes, tag, deploy verification.

---

## Tech debt

`docs/tech-debt.md` is the register. Items are numbered TD-01, TD-02, etc. Open items have severity (🔴 high · 🟡 medium · 🟢 low) and a cost-to-fix estimate.

If you spot new tech debt, append an entry. If you close existing debt, mark it ✅ Resolved with the sprint that closed it.

A full TD audit runs at every major version bump (next: v2.1 / v3.0).

---

## Deployment

Code merged to `main` does NOT auto-deploy. The maintainer deploys via `gcloud run deploy --source .` from a local clone.

**Always pass `--account admin@tamilfoundation.org --project sjktconnect`**. Never `gcloud config set`.

**Always use `--update-env-vars`** (merges) over `--set-env-vars` (silently wipes existing vars).

After every backend deploy: `./backend/scripts/update_jobs.sh` — mandatory job sync.

Read `CLAUDE.md` and `docs/release-notes-v2.0.1.md` Deployment State sections before deploying.

---

## Reporting bugs

- **Security-sensitive** (e.g. data leak, auth bypass, sensitive endpoint discovery): email admin@tamilfoundation.org directly. Do not open a public issue.
- **All others**: open a GitHub issue at https://github.com/tamilfoundation/sjktconnect/issues with: what you saw, what you expected, steps to reproduce, browser/locale if frontend.

---

## License

This project's license is in `LICENSE`. Your contributions are licensed under the same terms.

---

## Getting help

Stuck? Email admin@tamilfoundation.org. Single developer, best-effort response, but real.

Last reviewed: 2026-06-26 (v2.0.1).
