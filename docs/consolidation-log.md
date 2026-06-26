# Small-Change Lane — Consolidation Log

Per `Settings/_workflows/small-change-lane.md`. Each small-lane change appends one line under `## Pending`. Every ~10 entries triggers a Consolidation Review under `## Reviews`.

## Pending

- 2026-06-26 ops(cloudflare): legacy /claim + ASPX URLs 301 to root (Cloudflare ruleset `1af056d066e44a5885c933227a413981`, no repo code changes; closes 148+ of 157 GSC 404s from the 2026-06-26 SEO audit)
- 2026-06-27 fix(suggest-form): success-state button label "Cancel" → "Close" — owner-flagged UX bug. New i18n key `close` added across en/ms/ta (commit `cf09c7d`, 4 files)

## Reviews

_(none yet — review triggers when wat_lint flags the backlog)_
