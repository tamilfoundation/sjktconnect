# Sprint 28 Retrospective — SEO URL Slug + Alias Bridge + Phone Validation

**Closed**: 2026-06-26
**Wall time**: ~2.5h. 3 owner-flagged items.
**Scope**: ~18 files. Frontend slug rework, backend alias-generator extension, validation tightening.

## What Was Built

1. **URL slug**: `/school/<name>-<city>-<moe>` shape via new `lib/urls.ts` helper. Page handler accepts slug OR legacy bare-code; 301-redirects non-canonical to canonical. Sitemap + JSON-LD + meta canonical all emit slug. Admin-internal callsites still emit bare-code and rely on the redirect (good enough for non-public surfaces).
2. **Alias generator extension**: `Bhg ⇔ Bahagian ⇔ Division` automatic bridge in `seed_aliases.py`. Closes the root cause of Sprint 27's NBD4079 mis-tagging at the proper layer (aliasing) rather than at the fallback (Strategy 5).
3. **Phone validation**: replaced the permissive `{6,20}` shape regex with MY-specific digit-count rule (mobile 10-11, landline 9-10). `+60` international form normalised to local. Truncated numbers now fail; canonical shapes still pass.

## What Went Well

- **Acted on owner feedback to investigate from the aliasing angle, not Strategy 5.** I had proposed patching Strategy 5; owner pushed back ("we use aliases to tag, the issue must be in aliasing"). Reading `seed_aliases.py` made the gap obvious — no Bhg/Bahagian bridge in the generator. The proper fix is one block of code that runs for every future school, not a per-school migration. Sprint 27's hansard/0010 migration becomes belt-and-braces; future schools with these tokens are covered automatically.
- **URL slug shape preserves both old and new URLs.** Legacy `/school/PBD1088` still works (no 404s for existing inbound links), and Google sees the 301 → canonical slug to converge indexing.
- **Phone validation fix was small.** The bug was "regex too permissive" not "wrong design"; tightening the rule + adding +60 normalisation = 15 lines of code + 6 test cases.

## What Went Wrong

- **I proposed the wrong fix layer in the previous response.** Owner correctly pointed at aliasing as the proper mechanism. I'd jumped to "patch Strategy 5" when the root issue was that Strategy 1.5 (alias lookup) had no aliases to find. Lesson: when the user pushes back on a proposed fix, take the pushback seriously before defending the original. Often they're seeing the architecture more clearly because they're not deep in implementation details.
- **Test churn for the slug change was real.** 4 component tests had hardcoded bare-code URLs in assertions; updating them is mechanical but easy to miss if you don't run the full suite. Caught at sprint test run, not at deploy. Acceptable.
- **The `_GENERIC_WORDS` list in Strategy 5 is still missing `bahagian` and `division`** even after Sprint 28. If the alias generator doesn't fire for a school (e.g. seed_aliases not re-run after a backend deploy, which the workflow guards against but humans can miss), Strategy 5 would still mis-fire. Logged as a low-priority follow-up: defensive belt-and-braces by extending `_GENERIC_WORDS` would prevent the false positive even when aliases are missing.

## Design Decisions

(See `docs/decisions.md` for new entries.)

1. **Slug shape: `<name>-<city>-<moe>` (name first, moe at end)** — name first maximises SEO keyword weight at the start of the URL path; moe at the end gives a clean parse-back regex.
2. **Page handler accepts BOTH slug and bare-code** — single source of truth (slug is canonical) without breaking existing inbound links. The 301 redirect converges Google.
3. **`isValidPhone` does digit-count, not full Malaysian-number lookup** — keeps the rule small and predictable. Doesn't try to validate that "010 + 12345678" is a real number, just that the SHAPE matches a Malaysian phone. Edge case of typo'd-but-shape-valid number is accepted; that's the right cost trade for code clarity.
4. **Alias generator extension over Strategy 5 patch** — owner's instinct was right: fix at the source layer, not the fallback. Strategy 5 stays as defence-in-depth.

## Numbers

| Metric | Sprint 27 close | Sprint 28 close | Delta |
|---|---|---|---|
| Backend tests | 1420 | **1424** | +4 |
| Frontend tests | 349 | **366** | +17 |
| Files touched | — | 18 | — |
| Wall time | — | ~2.5h | — |

## Operational follow-ups

- **Run `seed_aliases` on prod** — materialises Bhg/Bahagian/Division variants for the 4 schools that currently have those tokens (NBD4079, ABDB006, MBD0067, plus any newly-imported school in future). One-off shell command against prod or trigger via Cloud Run job override.
- **Re-resolve 7 mis-tagged Ladang Labu articles** — `rematch_schools` doesn't currently re-process articles that have wrong moe_codes (only un-matched ones). Either extend the command with a `--force-all` flag in a follow-up, or run a one-off Django shell to delete the wrong tags and re-analyse.
- **GSC manual indexing request for top-30 school pages** — push Google to pick up the new slug canonical URLs faster than the natural crawl cycle. Submit through Search Console URL Inspection.

## What I'd do differently

- **Surface the alias generator gap proactively after Sprint 24.** I added Strategy 1.5 (alias lookup) in Sprint 24 but didn't think to audit whether the generator was producing aliases comprehensive enough to be useful for news matching. The lesson "audit shared-state lookups before adding strategies" was about the LOOKUP path; I should generalise it to "when adding a lookup against a generated dataset, also audit the GENERATOR for completeness". Worth adding to lessons.md.
