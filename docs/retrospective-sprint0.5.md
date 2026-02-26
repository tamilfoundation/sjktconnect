# Sprint 0.5 Retrospective — Admin Review Queue + Content Publishing

**Date**: 2026-02-25
**Duration**: ~1 session (continued from Sprint 0.4 close)

## What Was Built

Admin review workflow for Hansard mentions and public Parliament Watch page:

- **MentionReviewForm** — ModelForm with ChoiceFields for AI analysis fields, TypedChoiceField for IntegerField significance
- **8 views**: 6 admin (login required) + 2 public
  - ReviewQueueView: sittings list with pending/approved/rejected counts
  - SittingReviewView: all mentions for one sitting
  - MentionDetailView: split-screen (Hansard excerpt left, editable form right)
  - ApproveMentionView: saves form edits + sets APPROVED
  - RejectMentionView: sets REJECTED + review_notes
  - PublishBriefView: generates brief + publishes
  - ParliamentWatchView: public grid of published briefs
  - BriefDetailView: public single brief page
- **URL wiring**: 8 parliament routes + login/logout at root
- **Template tag**: `highlight_keywords` — 6 regex patterns for SJK(T) variants
- **7 templates**: base (navbar/footer), queue, sitting_review, detail, watch, brief, login
- **CSS stylesheet**: variables, responsive grid, mention cards with status borders, highlight styling
- **49 tests**: views (33), highlight filter (12), form validation (4)

## What Went Well

1. **Roadmap accuracy**: Sprint 0.5 scope in the roadmap matched what was needed almost exactly. No scope creep.
2. **AuditLog integration for free**: Because HansardMention is already in AUDIT_LOG_MODELS (from Sprint 0.1), approve/reject actions automatically create audit entries. Tests verified this.
3. **Test coverage caught real bugs**: The test suite caught the significance IntegerField crash immediately — form submitted empty string, model expected int or None.
4. **Template tag was clean**: The highlight regex pattern list from the normaliser (Sprint 0.2) could be reused directly.

## What Went Wrong

1. **Redirect bug in approve/reject views**: Initially redirected to `mention-detail` with `pk=mention.sitting_id` — this would look up a HansardMention by the sitting's PK (wrong model). Caught during code review before tests ran. Fixed to redirect to `sitting-review`.
2. **TypedChoiceField not used initially**: ChoiceField with `required=False` saves empty string `''` — but IntegerField can't convert `''` to int. Needed `TypedChoiceField(coerce=int, empty_value=None)` to properly convert empty to None. Caught by tests.
3. **`markdown` module missing for Python 3.11**: Was installed for Python 3.13 but not 3.11. Caused import error during test collection. Not a code bug but a dev environment gap.

## Design Decisions

1. **Split-screen detail view**: Left panel shows context + highlighted verbatim quote + matched schools. Right panel has the editable form. This avoids rendering full Hansard PDFs (roadmap recommendation).
2. **Approve = save + status change**: One POST saves all form edits AND sets status to APPROVED. Simpler than separate "save" and "approve" buttons.
3. **Sitting-level navigation**: Queue → Sitting → Mention. The sitting is the natural grouping since reviewers process all mentions from one sitting together.
4. **Blank choices with `("", "---")`**: Allows reviewers to clear AI-assigned values if the AI got something wrong.
5. **PublishBriefView handles None gracefully**: If `generate_brief()` returns None (no analysable mentions), the view simply redirects without error.

## Numbers

| Metric | Value |
|--------|-------|
| Files created | 12 (forms, views, urls, templatetag, 7 templates, CSS) |
| Files modified | 2 (sjktconnect/urls.py, parliament/forms.py fix) |
| Tests added | 49 |
| Total tests | 198 |
| Views | 8 |
| Templates | 7 |
| URL patterns | 8 + 2 (auth) |
| Bugs caught by tests | 1 (significance empty string) |
| Bugs caught by review | 1 (redirect target) |
