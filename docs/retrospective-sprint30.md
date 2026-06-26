# Sprint 30 Retrospective — v2.0.1 Release + Production Folder Move

**Closed**: 2026-06-26
**Wall time**: ~2.5h end-to-end (release notes + tagging + folder move + recovery + project-complete docs)
**Scope**: tag a clean v2.0 narrative, move the project from `Development/` to `Production/`, kick off the project-complete workflow.

## What Was Built

1. **`docs/release-notes-v2.0.1.md`** (new, ~9KB) — rewrites the prior v2.0 draft (Sprint 24-era, covered Sprint 23+24 only) to cover the full v2.0 series narrative: Sprint 23 → Sprint 29 + 2026-06-26 small-change-lane. Each shipped feature references actual file:line in the codebase.
2. **`v2.0.1` git tag** on commit `ae075a1`. Annotated tag with message summarising what v2.0.1 adds over v2.0 (Sprint 25–29 + small-change-lane). v2.0 preserved as historical milestone marker.
3. **Folder move** `Development/SJKTConnect/` → `Production/SJKTConnect/`. Workspace MEMORY.md row + memory/sjktconnect.md path + Settings/_shared/projects.json all updated.
4. **Workspace state** at v2.0.1: api `00135-kxm` + web `00127-vhh` + 7/7 jobs synced + 1436 backend tests + 367 frontend tests + Cloudflare ruleset with 3 rules + monthly-blast scheduler enabled.

## What Went Well

- **Release-notes rewrite was driven by primary sources, not memory.** Each feature line was checked against the actual code/migration file (`backend/schools/services/revalidation.py`, `frontend/lib/urls.ts`, `schools/0011_normalise_state_names`, etc.). Reduces the "retro says X but code says Y" drift documented in lessons.md (Sprint 17).
- **Recovery from the folder-move disaster was trivial** because v2.0.1 was already pushed to origin BEFORE attempting the move. The mv-partial-failure lost most of the working tree (backend/, frontend/, docs/, .git/), but `git clone https://github.com/tamilfoundation/sjktconnect.git` restored everything in ~30 seconds. The .env was the only gitignored content, and it survived in the broken dir for the user to move over manually.
- **Honest scope-walk back when initial design overreached.** Sprint 30 was originally framed as "SEO follow-up + release" with school-page body-content beef-up + FAQ accordion. Owner pushed back: school pages don't need redesign; the thin-content gap is on DUN/constituency pages. Walked the scope back to (B) Cloudflare 301s only via small-change-lane, then converted Sprint 30 entirely into the release + folder move work. Better to ship a small focused sprint than a misframed large one.
- **v2.0.1 framing preserved historical record** rather than rewriting the published v2.0 tag. Owner-decided. Conventional git etiquette held.

## What Went Wrong

- **`mv Development/SJKTConnect Production/SJKTConnect` failed catastrophically on Windows.** Both Unix `mv` and PowerShell `Move-Item` errored partway with file-lock issues. The partial completion LOST `backend/`, `frontend/`, `docs/`, `.git/` — only 5 top-level files survived in the new location. **Root cause**: this session had run `pytest`, `npm test`, `npm run build` against the project earlier; node_modules + pytest caches + a `nul` file artifact were still holding Windows file handles even after those commands completed. Windows doesn't release handles eagerly the way Unix does. The mv started moving files, hit a locked one, and aborted — but had already moved the unlocked ones, leaving an unrecoverable partial state. **System change**: lesson added — for any cross-directory move of a recently-active git working tree on Windows, prefer `git push` everything → `git clone` fresh at the target path → move `.env` manually → delete the old dir. Avoids file-lock hell. The `mv` pattern only works reliably when the dir hasn't had npm/Node touching it in the current session.
- **`.gitconfig includeIf` rule was keyed on `Development/SJKTConnect`, didn't match `Production/SJKTConnect`.** After the fresh clone at the new path, the first `git commit` failed with "unable to auto-detect email address". The workspace MEMORY.md note said "auto-configured via .gitconfig includeIf" — but includeIf is path-keyed, and the path changed. **Root cause**: when projects move between `Development/` and `Production/` directories, path-based includeIf rules silently stop matching. **System change**: set `git config user.email/user.name` locally per repo after any path-changing move. Workspace MEMORY.md row updated to reflect path change. Future fix: broaden the .gitconfig includeIf pattern to match `**/SJKTConnect/**` regardless of parent directory, OR document the local-config step in this project's CLAUDE.md under "Deployment / Folder Operations".
- **v2.0 tag already existed on origin — discovered at tag-time.** The prior session at Sprint 24 close (2026-06-26 early) had tagged v2.0 covering Sprint 23+24 only. Sprint 30 tried to tag v2.0 again for the full Sprint 23→29 narrative. **Root cause**: previous sprint-close didn't update memory to record the tag had been created, so subsequent sessions weren't aware of the existing tag. **System change**: when creating a release tag, check `git ls-remote --tags origin <version>` FIRST as part of the release.md workflow. If the tag exists, ask the user (force-update vs version-bump). Sprint 30 picked version-bump → v2.0.1; lesson generalises to "always check for existing tags before tagging".
- **Skipped writing this retrospective on first close.** The user had to ask "Have you written release notes, readme, etc.?" to surface that project-complete.md workflow was skipped (LICENSE / CONTRIBUTING.md / docs/sla.md / docs/roadmap.md / Sprint 30 retro / final TODO/FIXME sweep / README rewrite — all missing). **Root cause**: focused on the release.md workflow (which I read) but didn't read project-complete.md cover-to-cover. The release was conflated with the project-complete milestone in my mental model. **System change**: when closing a sprint that moves a project into production maintenance mode, run BOTH release.md AND project-complete.md. The two workflows are distinct: release covers tag + notes + deploy verification; project-complete covers governance + onboarding + final cleanup. Marked Sprint 30 close as still-in-progress until both are done.

## Design Decisions

(Full entries in `docs/decisions.md`.)

1. **v2.0.1 over force-updating v2.0.** Conventional git etiquette: don't rewrite published tags. Even on a private nonprofit single-developer repo, force-updating breaks the audit trail if anyone (or anything — CI, mirrors) pulled the old tag. Cost of an extra tag = zero. Cost of rewriting = small but real reputational/auditability hit. Chose v2.0.1.
2. **Recovery via fresh `git clone` over copy-then-rsync.** Once mv had partial-failed, options were (a) cp -r partial dir to new location + manually re-fetch missing pieces from origin, or (b) wholesale fresh clone. (b) wins on simplicity and integrity — guaranteed match with origin/main, no manual diff to verify. Took 30s; the .env was the only manual step (sandbox blocks .env operations).
3. **Per-repo `git config user.email` over patching `.gitconfig` includeIf.** Local config is repo-scoped and survives subsequent path moves. Patching includeIf to match `**/SJKTConnect/**` would also work but spreads project knowledge into a global file. Per-repo wins on locality.

## Numbers

| Metric | At Sprint 29 close | At Sprint 30 close | Delta |
|---|---|---|---|
| Backend tests | 1436 | 1436 | 0 (release sprint, no code) |
| Frontend tests | 367 | 367 | 0 |
| Git tags | v2.0 | v2.0 + v2.0.1 | +1 |
| Project folder | `Development/SJKTConnect/` | `Production/SJKTConnect/` | moved |
| Wall time | — | ~2.5h | ~30 min was mv-recovery + 30 min was project-complete catch-up |
| Files written this sprint | — | `docs/release-notes-v2.0.1.md` (new), `docs/retrospective-sprint30.md` (this file, new), `README.md` (full rewrite), `CHANGELOG.md` (1 line), `CLAUDE.md` (Project Status + Next Sprint), workspace memory files, `docs/sla.md` (new), `docs/roadmap.md` (new), `CONTRIBUTING.md` (new), `LICENSE` (new, pending owner choice) | — |

## Operational state at close

- **Prod api**: `sjktconnect-api-00135-kxm` (Sprint 29 + small-change-lane, unchanged)
- **Prod web**: `sjktconnect-web-00127-vhh` (Sprint 29 + small-change-lane, unchanged)
- **Jobs**: 7/7 synced
- **Schedulers**: all 4 enabled (monthly-blast + fortnightly-digest + resume-sending + urgent-alerts)
- **Cloudflare ruleset** `1af056d066e44a5885c933227a413981`: 3 rules (claim-* 301, ASPX 301, www-canonical)
- **Folder**: `Production/SJKTConnect/` (moved this sprint)
- **Git tags on origin**: `v2.0` (Sprint 23+24 narrative), `v2.0.1` (full v2.0 series)
- **Open tech debt**: TD-12 (hansard extractor 26% coverage, deferred), TD-06/TD-24 (egress checkpoint operational follow-up)

## Pending follow-ups (out of sprint scope)

- **2026-07-17 GSC validation pull** — confirm Sprint 28 URL slug + small-change-lane 301s shifted the numbers.
- **TD-06 / TD-24 egress dashboard check** — 1-line operational task at console.cloud.google.com.
- **LICENSE choice** — Sprint 30 didn't ship LICENSE; pending owner pick of license type (MIT, Apache 2.0, GPL, proprietary).

## What I'd do differently

- **Run both `release.md` AND `project-complete.md` together when a sprint flips a project into production maintenance mode.** They're distinct workflows but the sprint that crosses that threshold needs both. I treated them as serial alternatives and ran only one.
- **Sanity-check for existing tags before tagging.** `git ls-remote --tags origin v<version>` as the first step of `release.md` step 4. Costs 1 second; avoids the v2.0-already-exists discovery mid-tag.
- **Avoid `mv` for cross-directory folder moves on Windows after a session that's touched node_modules.** Clone fresh from origin at the new path; that's the only reliable pattern. Documented in lessons.md.
- **Set local git identity immediately after any clone, before the first commit.** `git config user.email admin@tamilfoundation.org && git config user.name Tamilfoundation`. Don't rely on includeIf to inherit identity at a new path.
