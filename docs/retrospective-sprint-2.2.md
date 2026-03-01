# Sprint 2.2 Retrospective — Broadcast Models + Admin Compose UI

## What Was Built

New `broadcasts` Django app providing the data layer and admin UI for composing email broadcasts to filtered subscribers:

- **Models**: `Broadcast` (subject, HTML/text content, audience filter JSON, status lifecycle, created_by audit) and `BroadcastRecipient` (per-email delivery tracking with denormalised email for audit trail)
- **Audience service**: `get_filtered_subscribers(filter_dict)` filters active subscribers by subscription category, state, constituency, PPD, enrolment range, and SKM eligibility
- **Admin views**: Compose form (`/broadcast/compose/`), preview (`/broadcast/preview/<id>/`), and list (`/broadcast/`) — all behind LoginRequiredMixin
- **Templates**: Compose form with all audience filters, sandboxed HTML preview, paginated broadcast list

## What Went Well

- Subagent-driven development produced a complete, working app in one pass — 17 files created
- Two-stage review (spec compliance + code quality) caught real issues before they became problems
- Code review caught a stored XSS vulnerability via `|safe` — fixed with sandboxed iframe
- Audience service cleanly separated from views, making it reusable for Sprint 2.3 sending
- Dynamic state/PPD dropdowns queried from DB rather than hardcoded — survives data changes

## What Went Wrong

- Subagent fix for code review issues was assumed to be isolated (worktree) but actually wrote to main tree — caused confusion about what was committed vs not
- `auto_now_add` ordering test failed (same pattern from lessons.md Sprint 2.1) — fixed by testing `Meta.ordering` instead of queryset comparison
- Initial implementation had no server-side validation for the compose form — would have caused empty broadcasts and 500 errors on bad input

## Design Decisions

1. **Sandboxed iframe for HTML preview** (vs bleach/nh3 sanitisation): Chose iframe with `sandbox=""` attribute because it's zero-dependency and blocks all scripts/forms/navigation. Sanitisation will be needed at send time (Sprint 2.3) but isn't required for admin-only preview.

2. **JSONField for audience_filter** (vs separate filter model): JSON allows flexible, extensible filtering without schema changes. Filters are simple key-value pairs interpreted by the audience service.

3. **Dynamic state/PPD dropdowns** (vs hardcoded list): Queries `School.objects.values_list().distinct()` to avoid stale data if schools are added/removed.

4. **created_by audit field**: Added during code review — records which admin composed each broadcast for accountability.

## Numbers

- Files created: 17 (app structure + templates)
- Files modified: 3 (settings, urls, base.html)
- New tests: 47 (13 model + 15 audience service + 19 views)
- Total tests: 484 backend passing
- Code review iterations: 1 (all issues fixed in single pass)
