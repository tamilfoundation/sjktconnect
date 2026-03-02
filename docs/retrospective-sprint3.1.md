# Sprint 3.1 Retrospective — Data Quality + School Leadership

**Date**: 2 March 2026
**Duration**: Single session (~2 hours)
**Execution**: Subagent-driven development (3 implementer dispatches + 1 spec review)

## What Was Built

1. **Data quality utilities** (`schools/utils.py`):
   - `to_proper_case()`: converts ALL CAPS MOE text to proper title case, preserving ~15 abbreviation categories (SJK(T), PPD, LDG, Roman numerals, etc.)
   - `format_phone()`: standardises Malaysian phone numbers to `+60-X XXX XXXX` format
   - 32 unit tests covering edge cases

2. **Data migration** (`0003_proper_case_data.py`):
   - Applied proper case to all 528 schools: name, short_name, state, ppd, address, city
   - Lowercased all emails, formatted all phone/fax numbers
   - Import scripts updated to apply transformations on future imports

3. **File reorganisation**:
   - Moved 6 root-level data files to `data/` subfolder
   - Updated all import script paths
   - Cleaned `.gitignore` for `.pytest_cache`

4. **SchoolLeader model** (`0004_add_school_leader.py`):
   - Four roles: Board Chairman, Headmaster, PTA Chairman, Alumni Association Chairman
   - Conditional unique constraint (one active leader per role per school)
   - Admin inline for managing leaders
   - Public API exposes name + role only (phone/email kept private)
   - Custom role ordering via Case/When (Chairman → HM → PTA → Alumni)
   - 10 tests (7 model + 3 API)

## What Went Well

- **Subagent-driven execution worked smoothly**: 3 implementer dispatches completed all 6 backend tasks with minimal intervention
- **Proper case utility is comprehensive**: handled edge cases well (apostrophes, Roman numerals, dot-joined tokens, parenthetical expressions)
- **Privacy-first API design**: leadership contacts expose name+role publicly but keep phone/email admin-only by default
- **No test regressions**: existing tests updated correctly when ALL CAPS assertions changed to proper case
- **Clean separation**: utilities in `utils.py` are reusable for any future data imports

## What Went Wrong

- **Session context consumed quickly**: design discussion + approval + implementation + sprint close pushed context limits. The implementation plan has 15 tasks across 3 sprints, but only 6 tasks (Sprint 3.1) fit in one session.
- **Edit tool requires read-first**: initial attempts to edit import scripts failed because files hadn't been read yet. Minor friction, quickly resolved.

## Design Decisions

1. **Proper case at database level** (not display-time): one-time migration + import-time transformation. Avoids repeated runtime processing.
2. **SchoolLeader as separate model** (not JSON field): allows proper constraints, admin inline, and future API filtering.
3. **Conditional unique constraint**: `is_active=True` filter allows historical records while ensuring only one active leader per role.
4. **Custom ordering in serializer** (not model Meta): model uses alphabetical ordering for admin, serializer uses Case/When for public display order.
5. **Design doc before code**: full design document reviewed and approved before any implementation began.

## Numbers

| Metric | Value |
|--------|-------|
| Backend tests | 662 (was 621) |
| Frontend tests | 179 (unchanged) |
| Total tests | 841 |
| New tests | 41 |
| Files created | 6 |
| Files modified | 7 |
| Migrations | 2 (0003 data, 0004 schema) |
| Schools migrated | 528 |
