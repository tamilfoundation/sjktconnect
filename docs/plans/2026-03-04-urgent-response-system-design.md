# Urgent Response System — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Phase:** 4 (Advocacy & Action)

## Problem

The news pipeline flags urgent articles (safety crises, closure threats, funding cuts) with a red URGENT badge. But nothing happens after that. No one is notified, no action is taken, and the badge is meaningless decoration.

## Solution

Turn urgent news detection into an actionable advocacy workflow:

1. AI detects urgency and **drafts a response** (action brief + formal letter)
2. Admin reviews, edits, and **sends the letter** to the responsible party
3. Affected school is **CC'd** so they know someone is advocating for them
4. Public readers can **take action** — share, support the cause, or contact the responsible party directly

## Design

### 1. Enhanced AI Analysis

When `is_urgent=True`, a second Gemini Flash call generates:

- **responsible_parties**: List of who should act (e.g. "Ipoh City Council (MBI)", "MP for Ipoh Barat")
- **action_type**: Category — `safety`, `funding`, `policy`, `closure_threat`, `personnel`
- **suggested_actions**: What specifically needs to happen
- **action_brief**: Structured summary for the admin — what happened, who's affected, who should act, why it's urgent
- **draft_letter**: Formal letter addressed to the primary responsible party, professional tone, referencing the article, stating the concern, requesting specific action

The responsible party depends on the article content:
- PTA complaining about road safety → local council + MP/ADUN + Ministry of Transport
- School admin cited as the problem → MOE
- Lack of funding from MOE → MOE needs pressure
- The AI identifies this from the article context.

### 2. Model Changes

Three new fields on `NewsArticle` (no new models for this part):

| Field | Type | Purpose |
|-------|------|---------|
| `action_brief` | TextField, nullable | Situational summary for admin |
| `response_draft` | JSONField, nullable | Letter, responsible parties, action type, audit trail |
| `response_status` | CharField, nullable | `PENDING` / `SENT` / `DISMISSED` |

`response_draft` JSON structure:
```json
{
  "letter": "Dear Sir/Madam...",
  "responsible_parties": ["Ipoh City Council (MBI)", "MP for Ipoh Barat"],
  "action_type": "safety",
  "suggested_actions": "Repair speed bumps, install rumble strips",
  "sent_to": ["mbi@ipoh.gov.my"],
  "cc": ["ABD1234@moe.edu.my", "headmaster@email.com"],
  "sent_at": "2026-03-04T10:30:00Z",
  "sent_by": "admin"
}
```

One new model:

| Model | Fields | Purpose |
|-------|--------|---------|
| `ActionSupporter` | article (FK), name, email, comment, created_at | Public supporters of urgent causes |

### 3. Admin Notification

When the pipeline processes an urgent article:
- Brevo email sent to admin: "Urgent: [title] — Action brief ready for review"
- Direct link to the Django admin review page
- Fallback: urgent articles show a banner in the admin review queue

### 4. Admin Review UI

Existing article detail view in admin gets a new **"Urgent Response"** panel:

- **Action Brief** — formatted read-only summary
- **Responsible Parties** — listed with any contact info from the system (MP name/party from Constituency model, school contacts)
- **Draft Letter** — editable textarea, pre-filled by Gemini
- **Actions:**
  - **Send as Email** — opens broadcast compose pre-filled with letter + targeted audience
  - **Download as PDF** — letter-format PDF for printing/attaching
  - **Dismiss** — marks as reviewed, no action needed

### 5. Letter Sending + School CC

When the admin sends a letter:

- **Primary recipient**: Responsible party email (manually entered by admin for now)
- **CC**: Affected school's `[moe_code]@moe.edu.my` + SchoolLeader emails on file (headmaster, PTA chair, board chair) if relevant
- **Format**: Professional letter template via Brevo — letterhead, date, addressee, body, signature, CC list
- **Audit trail**: Stored in `response_draft` JSON — who was sent what, when, CC list

### 6. Public Action Panel (Frontend)

When an urgent article has an active response, the NewsCard on tamilschool.org shows a **"Take Action"** panel with three tiers:

**Tier 1 — Share (lowest effort):**
- WhatsApp, Facebook, X share buttons with pre-written message
- One-tap sharing

**Tier 2 — Support this cause (medium effort):**
- Inline form: name + email + optional comment
- Counter: "47 people support this cause"
- Supporter list attachable to formal letter as appendix
- Soft subscribe prompt for non-subscribers

**Tier 3 — Contact directly (highest effort):**
- Who the responsible party is + what action is needed
- Template message ready to copy-paste into email or social media
- Responsible party contact details if known

### 7. Data Flow

```
Daily pipeline (8:30 AM)
  -> fetch_news_alerts
  -> extract_articles
  -> analyse_news_articles (Gemini Flash)
      -> relevance, sentiment, schools, is_urgent
      -> IF is_urgent:
          -> generate_response_draft (Gemini Flash, 2nd call)
          -> send admin notification email
          -> response_status = PENDING

Admin flow:
  -> Gets email notification
  -> Reviews action brief + draft letter in admin
  -> Edits letter if needed
  -> Sends (with school CC) / Downloads PDF / Dismisses
  -> response_status = SENT or DISMISSED

Public flow:
  -> Sees urgent article on tamilschool.org
  -> Take Action panel appears (if response active)
  -> Shares / Supports / Contacts responsible party
```

### 8. Error Handling

| Failure | Behaviour |
|---------|-----------|
| Gemini response draft fails | Article still marked urgent, brief stays null. Admin notified with "manual review needed". |
| No school matched | Brief and letter still generate but without school-specific context. Admin fills in gaps. |
| Brevo send fails | Per-recipient SENT/FAILED tracking. Admin sees failure, can retry. |
| Admin email not delivered | Urgent articles show banner in admin review queue as fallback. |

## Future Phase

- **Contact directory**: Harvest MP/ADUN/government body email addresses for auto-populated recipients
- **Multi-language letters**: BM and Tamil versions of the letter
- **Response tracking**: Did the responsible party respond? Follow-up workflow.
- **Subscriber alerts**: Auto-notify relevant subscribers when an urgent article is detected in their area

## Files Affected

- `backend/newswatch/models.py` — 3 new fields + ActionSupporter model
- `backend/newswatch/services/news_analyser.py` — response draft generation
- `backend/newswatch/services/response_drafter.py` — new service for Gemini 2nd call
- `backend/newswatch/views.py` — urgent response admin panel
- `backend/newswatch/templates/` — response panel template, letter PDF template
- `backend/newswatch/api/serializers.py` — expose response data to frontend
- `frontend/components/NewsCard.tsx` — Take Action panel
- `frontend/components/TakeActionPanel.tsx` — new component
- `frontend/components/ShareButtons.tsx` — new component
- `frontend/components/SupportForm.tsx` — new component
