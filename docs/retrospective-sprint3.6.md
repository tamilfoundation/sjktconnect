# Sprint 3.6 Retrospective — Footer, Legal, Contact, School Page & Map Filters

**Date**: 2026-03-03
**Duration**: 1 session

## What Was Built

1. **Footer redesign** — Multi-column dark footer matching Stitch design
2. **3 legal pages** — Privacy Policy, Terms of Service, Cookie Policy (trilingual)
3. **Contact form** — Frontend form + backend API with Brevo email integration
4. **School detail page redesign** — Sidebar filled, leadership always shown, 5 stat cards, clickable constituency/DUN links, visual polish
5. **Map filter panel** — 4 colour modes with toggle switches, dynamic pin colours, enrolment slider
6. **Search fix** — SJKT↔SJK(T) normalisation

## What Went Well

- **Stitch-first design**: Having Stitch mockups before coding made implementation precise
- **Batch approach**: 4 batches kept scope manageable within context limits
- **Test coverage**: 10 new MapFilterPanel tests, updated SchoolProfile + ConstituencySchools tests
- **No breaking changes**: All existing tests continued to pass throughout

## What Went Wrong

- **DB connection issue**: Backend tests couldn't run initially due to stale `test_postgres` connections — solved with `--keepdb` flag
- **Context carryover**: Session continuation required careful reconstruction of prior work state

## Design Decisions

- **StateFilter kept but unused**: Not deleted — no longer imported anywhere but test file still exists for reference
- **School page sidebar**: Political representation moved from main content to sidebar card — fills the previously empty right column
- **Leadership placeholders**: Show "Headmaster" and "PTA Chairman" with "Not Available" rather than hiding the section entirely
- **Map filtering**: Replaced simple state dropdown with multi-dimensional colour-by filter (4 modes). State filter removed in favour of richer categorisation.
- **Enrolment mode**: Shows all schools but colours at/below threshold red — doesn't hide them

## Numbers

- **Tests**: 757 (532 backend + 225 frontend) — up from 747
- **New files**: 6 (ContactForm, MapFilterPanel, contact page, privacy page, terms page, cookies page)
- **Modified files**: 18
- **Translation keys added**: ~80 across 3 languages (mapFilters, contact, legal namespaces)
