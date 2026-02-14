# SJK(T) Connect — Product Requirements Document

**Version**: 0.2 (Draft)
**Date**: 14 February 2026
**Status**: Draft — Pending Review
**Prepared for**: Tamil Foundation Board
**Author**: Tamil Foundation / Elan

---

## 1. Executive Summary

Tamil Foundation (TF) has compiled data on Malaysia's 528 SJK(T) (Tamil primary schools) over many years — student populations, teacher counts, school boards, headmasters, GPS coordinates, contact details, and infrastructure status. This data has historically been maintained by a single staff member and stored in spreadsheets. The project wound down when the data became less immediately useful, and it now sits static.

**The Problem**: School data changes constantly (headmasters transfer, boards rotate, enrolment shifts yearly). One person cannot keep up. Meanwhile, Tamil schools are frequently discussed in Parliament, covered in news media, and affected by government policy — but no organisation systematically tracks, analyses, or responds to these developments. TF has the data and the relationships, but no platform to turn them into sustained advocacy.

**The Solution**: SJK(T) Connect — an intelligence and advocacy hub that flips the traditional model. Instead of asking schools for data and getting silence, TF **pushes high-value intelligence first** (parliamentary analysis, news monitoring, grant alerts) and collects verified school data as a byproduct. The system operates as three layers:

1. **Intelligence Engine** — AI-powered monitoring of Parliament (Hansard), news media, and government policy affecting Tamil schools, producing ready-to-publish analysis with minimal human input
2. **Advocacy Platform** — A public-facing map and directory of all 528 schools at `tamilschool.org.my`, with constituency pages, school profiles, and MP scorecards
3. **Communications Hub** — Automated broadcast system that delivers intelligence to schools, community leaders, journalists, and MPs, while collecting verified school data through Magic Link interactions

**Why now**: TF owns `tamilschool.org.my`, has working relationships with all four key stakeholder networks (LPS Federation, Headmasters' association, Former students' associations, Tamil Teachers Union), has verified GPS data for 95% of schools, and has official MOE email addresses for 526 of 528 schools. The missing piece is the platform.

**Technology**: Next.js + Django REST + Supabase + Gemini API, hosted on Cloud Run. Estimated cost: **$5-20/month**.

---

## 2. Problem Statement

### 2.1 The Data Decay Problem

TF's school database was last actively maintained when a full-time staff member updated it. Without that person, the data degrades:
- Headmasters transfer every 3-5 years
- PIBG committees rotate annually
- Enrolment shifts yearly
- Contact details go stale

**Result**: The data TF spent years building is increasingly unreliable, and rebuilding it through surveys fails because schools are fatigued by data requests that yield no return value.

### 2.2 The Intelligence Gap

Tamil schools are discussed in Parliament, covered in news media, and affected by government circulars — but no organisation systematically:
- Monitors what MPs say about Tamil schools in Hansard
- Tracks which MPs raise Tamil school issues (and which never do)
- Analyses news coverage across Tamil, Malay, and English media
- Responds rapidly when policy changes or crises affect schools
- Translates government circulars into actionable guidance for schools

**Result**: The community is always reactive, always late, and always under-informed. Responses come days after events, if at all. No institutional memory exists of parliamentary commitments, broken promises, or long-term trends.

### 2.3 The Chicken-and-Egg Problem

Building a school platform requires contacts. Collecting contacts requires offering value. Offering value requires a platform.

**Resolution**: Parliament Watch breaks the deadlock. It requires zero contacts, zero school participation, and zero infrastructure beyond a script and an AI model. It produces high-value, time-sensitive content from entirely public data. The audience builds itself.

---

## 3. User Roles

| Role | Who | Access | Purpose |
|------|-----|--------|---------|
| **TF Admin** | Tamil Foundation staff (initially 1 person) | Full system access. Can broadcast, export, manage all schools, review AI drafts, publish content. | Central operations and editorial control |
| **School Rep** | Headmaster, PIBG Chair, or LPS member | Magic Link access to their school only. Can view and confirm/edit school data. Authenticated via `@moe.edu.my` email. | Data verification and school page management |
| **Public Visitor** | Anyone | Read-only access to public school map, constituency pages, Parliament Watch reports, and school profiles. | Information consumption, accountability |
| **Subscriber** | School reps, community leaders, journalists, MPs' offices | Receives email broadcasts (Intelligence Blasts, grant alerts, Parliament Watch). Can manage subscription preferences. | Ongoing intelligence consumption |
| **Field Partner** (Phase 3+) | Volunteer or partner org staff | View-only for assigned regions. Can submit "Verified Visit" reports. | On-ground data validation |

---

## 4. User Journeys

### 4.1 School Headmaster (Primary User)

```
Discovers school on map     Claims page via MOE email     Receives monthly intelligence
        |                           |                              |
        v                           v                              v
+---------------+           +---------------+              +---------------+
| "Are You on   |           | Magic Link    |              | Parliament    |
|  the Map?"    |---------->| Verification  |------------->| Watch + Grant |
| Finds school  |           | Reviews data  |              | Alerts arrive |
| on Google     |           | Confirms/edits|              | monthly       |
+---------------+           +---------------+              +---------------+
                                    |                              |
                                    v                              v
                            +---------------+              +---------------+
                            | School page   |              | Forwards to   |
                            | updated with  |              | PIBG, shares  |
                            | verified data |              | with teachers |
                            +---------------+              +---------------+
```

**Key interactions**:
- Discovery is passive (school finds itself on the map or receives email notification)
- Authentication is passwordless (MOE email Magic Link)
- Data verification takes <30 seconds (pre-filled, confirm or edit)
- Intelligence arrives monthly without any action required

### 4.2 Community Leader / Journalist (Subscriber)

```
Sees Parliament Watch     Subscribes for updates     Receives & shares intelligence
report shared online              |                              |
        |                         v                              v
        v                 +---------------+              +---------------+
+---------------+         | Enters email  |              | Monthly Intel |
| Reads report  |-------->| on subscribe  |------------->| Blast with    |
| on tamilschool|         | page          |              | MP scorecards |
| .org.my       |         +---------------+              | news analysis |
+---------------+                                        | grant alerts  |
                                                         +---------------+
```

### 4.3 TF Admin (Operator)

```
AI pipeline runs          Admin reviews drafts         Content published
automatically                     |                         |
        |                         v                         v
        v                 +---------------+          +---------------+
+---------------+         | 10-min review |          | Email blast   |
| Hansard PDF   |-------->| of AI-drafted |--------->| Social posts  |
| downloaded    |         | reports, posts|          | Website update|
| AI analyses   |         | one-pagers    |          | Auto-generated|
+---------------+         +---------------+          +---------------+
                                  |
                                  v
                          +---------------+
                          | Rejects or    |
                          | edits before  |
                          | publishing    |
                          +---------------+
```

**The human role is editorial judgement** — tone, timing, what to publish and what to hold — not content production.

---

## 5. Feature Requirements

### Feature A: Intelligence Engine (Backend CRM)

**Purpose**: Single source of truth for all 528 Tamil schools.

| Requirement | Description | Priority |
|------------|-------------|----------|
| A1. School Profile | GPS, MOE code, address, board members, headmaster, enrolment history, infrastructure status, school image (verified/unverified tags) | Must |
| A2. Broadcast Tool | Filter schools by state, district, constituency, enrolment size, SKM status. Send segmented email broadcasts. | Must |
| A3. Audit Trail | Every data change logged — who, when, old value, new value. Immutable. Essential for advocacy credibility. | Must |
| A4. Annual MOE Import | Bulk-import official enrolment data yearly from MOE Excel to keep baseline fresh without relying on school reps. | Must |
| A5. Contact Management | Track verified contacts per school (email, phone, claimed/unclaimed status). Track subscriber list. | Must |
| A6. School Image Library | Store and serve school building photos with tiered sourcing: (1) user uploads, (2) Google Places Photos, (3) Street View Static API (~70-80% rural coverage), (4) satellite fallback (100% coverage). One-time harvest cost: ~$5 for all 528 schools using existing GPS + API key. Tool: extend `verify_school_pins.py` or create `harvest_school_images.py`. | Should |

**Acceptance criteria for A1**:
- Each school has a unique profile page with all MOE data fields populated from Jan 2026 dataset
- GPS coordinates display on an embedded map
- Verification status shown (last verified date, by whom)
- School image displayed (fallback chain: user upload > Places photo > Street View > satellite)

### Feature B: Magic Link Updater (School-facing)

**Purpose**: Passwordless school data verification triggered by high-value content.

| Requirement | Description | Priority |
|------------|-------------|----------|
| B1. MOE Email Authentication | System checks submitted email against stored `@moe.edu.my` address (pattern: `[SCHOOL_CODE]@moe.edu.my`, e.g. `JBD0050@moe.edu.my`). If match, sends Magic Link. If no match, prompts to use official school email. **Why this works**: If you can access the school's MOE email, you're someone authorised at that school. When headmasters transfer, the new HM inherits the school email account — so the mechanism stays valid automatically. Google Workspace means inboxes are actively monitored. | Must |
| B2. Magic Link Flow | Secure, time-limited link. Mobile-friendly page shows: resource requested (top) + pre-filled school data to confirm (bottom). | Must |
| B3. Confirm or Edit | Two actions: [Yes, Confirm] saves with timestamp. [No, Edit] opens inline editing. Both count as verification. | Must |
| B4. Gated Resources | Premium content (grant application templates, detailed reports) gated behind Magic Link verification. | Should |
| B5. School Profile Card | "Download as PDF" — one-page printable profile card with school name, location map, enrolment, district, key stats. Headmasters can print and pin on notice boards. A beautiful, tangible artefact that says "your school matters" is worth more than a hundred emails asking for data. | Should |

**Acceptance criteria for B2**:
- Magic Link expires after 24 hours
- Link works on mobile browsers without app installation
- Page loads in under 3 seconds on 3G connection
- Pre-filled data matches latest MOE import + any prior verified edits

### Feature C: Public Advocacy Map

**Purpose**: Public-facing directory for the general public, donors, and parliamentarians.

| Requirement | Description | Priority |
|------------|-------------|----------|
| C1. Interactive Map | Map of all 528 schools with GPS pins. Cluster at zoom-out, individual pins at zoom-in. | Must |
| C2. School Pages | SEO-friendly page per school (`tamilschool.org.my/school/[code]`). Name, location, enrolment, district, constituency, school image. | Must |
| C3. Constituency Pages | Auto-generated page per parliamentary constituency (`tamilschool.org.my/constituency/[name]`). Lists schools, aggregate stats, MP name, Parliament Watch score. 122 constituency pages + 222 DUN pages. | Must |
| C4. Filters | Filter map by state, district, enrolment range, SKM status. | Should |
| C5. Search | Search by school name, code, district, or constituency. | Must |
| C6. Privacy | Hide personal phone numbers. Show only official school contact (MOE email, school phone). | Must |
| C7. "Claim This Page" | CTA on every school page linking to Magic Link claim flow (Feature B). | Must |
| C8. Partner Logos | Footer displays logos of endorsing organisations (Tamil Teachers Union, LPS Federation, HM Council pending). | Should |

**Acceptance criteria for C2**:
- All 528 school pages generated from MOE data at launch
- Each page has: school name (English + Tamil if available), MOE code, address, enrolment, teacher count, district, parliamentary constituency, DUN, map embed, school image
- Pages indexable by Google (server-side rendered)
- "Claim this page" button prominent above the fold

**Acceptance criteria for C3**:
- 122 parliamentary constituency pages auto-generated from existing mapping data
- Each page lists: all SJK(T)s in constituency, total students, total teachers, MP name (manually maintained or fetched), Parliament Watch score (when available)
- Top constituency (Port Dickson, 15 schools) used as showcase example

### Feature D: AI Review Layer

**Purpose**: Automated triage of community submissions and Magic Link edits.

| Requirement | Description | Priority |
|------------|-------------|----------|
| D1. Three-Tier Review | Auto-approve (low-risk), AI-approve + notify (medium-risk), flag for human (high-risk). | Should |
| D2. Sanity Checks | Enrolment plausibility (50→55 fine, 50→5000 flagged). Student-teacher ratio consistency. | Should |
| D3. Duplicate Detection | Same change submitted twice → merge. | Should |
| D4. GPS Verification | Use Google Places API to verify GPS corrections (tool already built). | Should |
| D5. Spam Filter | Obvious junk submissions filtered out. | Should |

**Note**: This is a Phase 3 feature. In Phases 0-2, all edits go through the TF Admin manually.

### Feature E: Parliament Watch — Automated Hansard Intelligence Pipeline

**Purpose**: AI-powered monitoring of Malaysian parliamentary proceedings for Tamil school mentions, producing ready-to-publish analysis.

**This is the first product. It launches in Phase 0.**

| Requirement | Description | Priority |
|------------|-------------|----------|
| E1. Hansard Collection | Scheduled script downloads new Hansard PDFs from parlimen.gov.my after each sitting day. PDFs are text-based (no OCR). Parliament sits ~70-80 days/year. | Must |
| E2. Keyword Extraction | Extract all passages mentioning Tamil school keywords: "SJK(T)", "sekolah Tamil", "sekolah vernakular", "SJKT", specific school names. | Must |
| E2a. School Name Matching | Link unstructured text mentions to specific School records. School names in Hansard are informal/abbreviated (e.g., "SJKT Ladang Kubang" for JBD0045). Uses `SchoolAlias` lookup table + PostgreSQL `pg_trgm` trigram matching. First pass: exact match against aliases. Second pass: trigram similarity. Confidence <80%: flag for human review. 528 schools is small enough that curated aliases outperform ML approaches. | Must |
| E3. AI Analysis | For each mention, Gemini determines: who said it (minister/backbencher/opposition), type of mention (budget/question/policy/throwaway), significance (new commitment vs routine), sentiment (advocating/deflecting/promising), change from previous sittings. | Must |
| E4. MP Scorecard | Longitudinal tracker: which MPs raise Tamil school issues, how often, how substantively. Which ministers give substantive vs generic replies. Which of the 122 constituencies with Tamil schools have MPs who've never mentioned them. | Must |
| E5. Constituency Context | When an MP speaks, auto-link to schools in their constituency ("Port Dickson has 15 SJK(T)s — the most in Malaysia"). | Must |
| E6. Content Generation | AI drafts: per-sitting brief (1 page), monthly intelligence report (3-5 pages), social media posts (quote cards, scorecard visuals), broadcast email. | Must |
| E7. Video Clip Extraction | Match Hansard text against YouTube auto-captions (youtube-transcript-api, free, no API key) from Parliament YouTube channel. Generate timestamped link or extract 30-60 second clip via yt-dlp. Cost: $0. A video clip of an MP actually saying the words — with TF's analysis overlaid — is far more shareable than a text quote. | Should |
| E8. Human Review Gate | All AI-generated content queued for TF Admin review (~10 minutes per sitting day). Nothing publishes automatically. **Review interface**: split-screen view. Left panel shows raw Hansard text with keyword highlights. Right panel shows AI-drafted analysis (editable). Action buttons: Approve, Edit, Reject. Queue shows all pending items sorted by sitting date. | Must |
| E9. Historical Baseline | Run pipeline against historical Hansard corpus (available 1959-2020, 3,684 PDFs) to establish long-term MP Scorecard baseline and parliamentary attention trends. | Should |

**Acceptance criteria for E3**:
- AI correctly classifies mention type (budget/question/policy/throwaway) with >85% accuracy on a test set of 20 manually labelled mentions
- Each analysis includes: MP name, constituency, party, verbatim quote, AI summary, significance rating (1-5), change indicator (new/repeat/escalation/reversal)

**Acceptance criteria for E4**:
- Scorecard tracks: total mentions, substantive mentions, questions asked, questions answered, commitments made, commitments broken
- Updated after every sitting day
- Accessible on website as standalone page and embedded in constituency pages

### Feature F: News Watch + AI Rapid Response

**Purpose**: Monitor news media for Tamil school mentions and draft responses, turning TF into a rapid-response communications operation.

| Requirement | Description | Priority |
|------------|-------------|----------|
| F1. News Sensors | Google News Alerts for Tamil school keywords (free, zero scraping). Catches stories across all outlets and languages. | Must |
| F2. Multilingual Monitoring | Monitor Tamil, English, and Malay sources. Most Tamil school news originates in Malay (MOE circulars) and English media. | Must |
| F3. AI Analysis | For each detected story: classify type (policy, crisis, funding, human interest), assess significance, identify affected schools/constituencies, draft summary. | Must |
| F4. Rapid Response Drafts | AI generates response package appropriate to trigger type — see response matrix below. | Must |
| F5. Response Matrix | Different trigger types produce different outputs (see Section 5.6.1). | Must |
| F6. Human Review Gate | All AI-generated responses queued for TF Admin. Nothing publishes automatically. **Review interface**: split-screen view. Left panel shows original news article/source. Right panel shows AI-drafted response (editable). Action buttons: Approve, Edit, Reject. | Must |
| F7. MOE Circular Monitor | AI monitors MOE website and state JPN pages for new circulars affecting vernacular schools. Drafts plain-language explainer + action steps + deadline. | Should |

#### 5.6.1 Response Matrix

| Trigger | AI generates |
|---------|-------------|
| Minister announces school fund, Tamil schools not mentioned | Press statement + infographic showing maintenance needs |
| Specific Tamil school closure reported | Data-backed response: enrolment history, list of other at-risk schools, TF position + social post |
| MP raises teacher shortage in Parliament | Amplification: quote card + TF commentary + teacher-student ratios across all 528 schools |
| Negative story (e.g., school mismanagement) | Contextual response: enrolment trends, funding history, systemic factors |
| Budget day | Same-day analysis: "What Budget 2027 means for Tamil schools" with allocation breakdown |
| MOE policy circular affecting vernacular schools | Plain-language explainer for schools + recommended actions + broadcast to subscribers |

**Output formats per trigger**:
- Press statement / official TF response (for media pickup)
- Social media posts (quote cards, infographics, commentary threads)
- Broadcast email to subscribers (Intelligence Blast)
- Data-backed one-pager (for MPs, journalists, donors)
- Talking points (for TF spokesperson or allies)

**Acceptance criteria for F4**:
- Response draft available within 30 minutes of trigger detection
- Each draft includes: summary of trigger, affected schools/constituencies, TF position, supporting data, call to action
- Draft clearly labelled as AI-generated, requiring human review before publishing

---

## 6. Technical Architecture

### 6.1 Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14 (App Router) | Public map, school pages, constituency pages, Magic Link forms. SEO via SSR. |
| Backend | Django REST Framework | Admin CRM, broadcast engine, AI pipeline orchestration, Magic Link generation. |
| Database | Supabase (PostgreSQL) | School golden record, audit log, subscriber list. RLS for row-level security. Free tier sufficient. |
| AI | Gemini Flash API | Hansard analysis, news analysis, content generation, data review. |
| Email | Brevo or Resend (free tier) | Broadcasts, Magic Links, Intelligence Blasts. Start with free tier (300 emails/day Brevo). |
| Maps | Google Maps JavaScript API | Public school map. Existing API key. |
| Images | Google Places + Street View + Satellite APIs | One-time harvest of school building photos. |
| PDF Processing | pdfplumber (Python) | Hansard text extraction. Free, no API key. |
| Video | youtube-transcript-api + yt-dlp | Parliament clip extraction. Free, no API key. |
| Hosting | Google Cloud Run | Same as all other TF projects. Scales to zero. |
| Domain | tamilschool.org.my | Shares TF's Google Workspace. DKIM/SPF/DMARC configured. |

### 6.2 Data Model (Core Tables)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `School` | Golden record for each of 528 schools | moe_code (PK), name, name_tamil, address, postcode, state, ppd, constituency, dun, email, phone, gps_lat, gps_lng, enrolment, teacher_count, preschool_enrolment, skm_status, grade, last_verified, verified_by |
| `SchoolHistory` | Yearly enrolment snapshots from MOE imports | school_code (FK), year, enrolment, teacher_count, preschool_enrolment, source |
| `SchoolImage` | Building photos (Places, Street View, satellite, user uploads) | school_code (FK), image_url, source_type, uploaded_by, created_at |
| `SchoolBoard` | PIBG committee members | school_code (FK), name, role, year, phone, email, verified |
| `Contact` | Verified contacts (HMs, PIBG chairs, LPS) | school_code (FK), name, email, role, magic_link_token, last_verified |
| `Subscriber` | Email subscribers (not necessarily school reps) | email, name, organisation, subscription_type, subscribed_at |
| `Constituency` | Parliamentary constituency reference | code, name, state, mp_name, mp_party, school_count, total_enrolment |
| `DUN` | State constituency reference | code, name, state, constituency_code (FK), adun_name, school_count |
| `HansardSitting` | One row per parliamentary sitting day | sitting_date, session, pdf_url, processed_at, mention_count |
| `HansardMention` | Each Tamil school mention extracted from Hansard | sitting_id (FK), mp_name, mp_constituency, party, verbatim_quote, ai_summary, mention_type, significance, sentiment |
| `MentionedSchool` | Links Hansard mentions to specific schools (bridge table — one mention can reference multiple schools) | mention_id (FK), school_code (FK), confidence_score, matched_by (alias/trigram/manual) |
| `SchoolAlias` | Known name variants for fuzzy matching | school_code (FK), alias, alias_type (official/short/malay/common_misspelling) |
| `MPScorecard` | Aggregated scorecard per MP | mp_name, constituency, total_mentions, substantive_mentions, questions_asked, last_mention_date |
| `NewsAlert` | Each detected news story | source, url, headline, language, detected_at, ai_summary, significance, response_status |
| `Broadcast` | Each email broadcast sent | subject, content, audience_filter, sent_at, recipient_count, open_count |
| `AuditLog` | Immutable record of all data changes | table_name, record_id, field, old_value, new_value, changed_by, changed_at |

**Volume estimates**:
- 528 school records (static base, updated yearly)
- ~200-400 Hansard mentions per year (70-80 sitting days)
- ~100-300 news alerts per year
- ~12 monthly broadcasts per year
- Supabase free tier (500 MB) sufficient for 10+ years

### 6.3 AI Pipeline Architecture

```
                    ┌──────────────────────────────────────────┐
                    │           SCHEDULED TRIGGERS              │
                    │  (Cloud Scheduler or cron on Cloud Run)   │
                    └────────┬────────────────┬────────────────┘
                             │                │
                    ┌────────▼──────┐  ┌──────▼────────┐
                    │  PARLIAMENT   │  │  NEWS WATCH   │
                    │  WATCH        │  │               │
                    │  1. Download  │  │  1. Check     │
                    │     PDF       │  │     Google    │
                    │  2. Extract   │  │     Alerts    │
                    │     text      │  │  2. Fetch     │
                    │  3. Search    │  │     article   │
                    │     keywords  │  │  3. Extract   │
                    │  4. Store     │  │     content   │
                    │     mentions  │  │  4. Store     │
                    └────────┬──────┘  └──────┬────────┘
                             │                │
                    ┌────────▼────────────────▼────────┐
                    │         GEMINI ANALYSIS           │
                    │  - Classify mention/story         │
                    │  - Assess significance            │
                    │  - Link to constituencies/schools │
                    │  - Generate analysis              │
                    └────────────────┬─────────────────┘
                                     │
                    ┌────────────────▼─────────────────┐
                    │       CONTENT GENERATION          │
                    │  - Per-sitting brief              │
                    │  - Monthly report                 │
                    │  - Social media posts             │
                    │  - Video clip extraction          │
                    │  - Press statement (if triggered) │
                    │  - Broadcast email draft          │
                    └────────────────┬─────────────────┘
                                     │
                    ┌────────────────▼─────────────────┐
                    │       HUMAN REVIEW QUEUE          │
                    │  TF Admin: ~10 min per sitting    │
                    │  Approve / Edit / Reject          │
                    └────────────────┬─────────────────┘
                                     │
                    ┌────────────────▼─────────────────┐
                    │         PUBLISH                   │
                    │  - Website (auto)                 │
                    │  - Email broadcast (triggered)    │
                    │  - Social media (manual post)     │
                    └──────────────────────────────────┘
```

**Execution model**: All pipelines run as **Cloud Scheduler + Cloud Run Jobs** (ephemeral execution). Parliament Watch triggers once daily during sitting periods. News Watch triggers via Google Alerts webhook (event-driven). No continuously running containers — this is what keeps Cloud Run costs at $0-5/month instead of $30-40/month.

### 6.4 Email Architecture

- **Sender domain**: `tamilschool.org.my` (shares TF's Google Workspace credentials)
- **Authentication**: DKIM, SPF, DMARC configured via Google Workspace
- **Provider**: Brevo free tier (300 emails/day) or Resend (100 emails/day free)
- **Deliverability strategy**: Batch sends at ~50/day during initial outreach to build sender reputation
- **Email types**:
  - Transactional: Magic Links, school claim notifications
  - Broadcast: Intelligence Blasts, Parliament Watch, grant alerts
  - Operational: Subscription confirmations, preference management

---

## 7. Implementation Roadmap

### Phase 0: Parliament Watch (Standalone — Immediate Start)

**Duration**: 2-3 weeks build + ongoing operation
**Dependencies**: None (public data only)
**Cost**: $3-10/month during sitting periods

| Deliverable | Description |
|-------------|-------------|
| Hansard scanner | Script to download new PDFs from parlimen.gov.my, extract text, search keywords |
| AI analysis pipeline | Gemini processes each mention: classify, score, summarise |
| MP Scorecard (initial) | Track mentions per MP from current and recent sittings |
| Content templates | Per-sitting brief, monthly report, social media post templates |
| Publishing workflow | AI drafts → Admin review queue → publish to TF website/social |
| Historical baseline (stretch) | Run pipeline against historical corpus for long-term trends |

**Exit criteria**: First 5 Parliament Watch reports published. At least 3 received engagement (shares, comments, media pickup).

### Phase 1: The Seed (Database + Public Map + Outreach)

**Duration**: 4-6 weeks
**Dependencies**: Phase 0 running, school image harvest complete
**Cost**: One-time ~$5 for image harvest + ongoing hosting

| Deliverable | Description |
|-------------|-------------|
| Data import | MOE Jan 2026 Excel → Supabase. All 528 schools loaded. |
| Public school map | Interactive map at `tamilschool.org.my` with all 528 pins |
| School pages | SEO-friendly page per school with profile data, map, image |
| Constituency pages | 122 parliamentary + 222 DUN pages with school lists, aggregate stats |
| "Claim This Page" flow | MOE email authentication + Magic Link verification |
| School Profile Card | Downloadable PDF per school for notice boards |
| Admin dashboard | TF can view all schools, see verification status, manage contacts |
| Email outreach | Batched notifications to all 526 schools over 4 weeks, endorsed by partner networks |
| Parliament Watch integration | Reports link to relevant constituency and school pages |

**Exit criteria**: Map live at `tamilschool.org.my`. At least 50 schools claimed. At least 200 subscribers.

### Phase 2: The Value (Broadcasts + Magic Links + News Watch)

**Duration**: 3-4 weeks
**Dependencies**: Phase 1 live, subscriber base >100

| Deliverable | Description |
|-------------|-------------|
| Broadcast tool | Filter audiences, compose and send email blasts |
| Magic Link gating | Premium resources (grant templates, detailed reports) gated behind verification |
| News Watch | Google Alerts integration + AI analysis pipeline |
| AI Rapid Response | Response drafting for news triggers + review queue |
| Monthly Intelligence Blast | Parliament Watch + News Watch combined into flagship monthly email |
| Subscription management | Subscribe/unsubscribe, email preferences |

**Exit criteria**: 3 monthly Intelligence Blasts sent. Open rate >50%. At least 1 rapid response published within 24 hours of trigger.

### Phase 3: The Platform (Scale + Partners)

**Duration**: 4-6 weeks
**Dependencies**: Phase 2 proven, >100 schools verified

| Deliverable | Description |
|-------------|-------------|
| AI Review Layer | Three-tier automated review of school data submissions |
| Field Partner role | View-only access for assigned regions, verified visit reports |
| WhatsApp channels | State-level broadcast channels (one-way) |
| Weekly digest | Automated weekly summary email |
| PIBG Registration Kit | AGM templates + QR code registration form for annual committee changeover |
| Grant alert service | Curated funding opportunities — e.g. "RM 50k Maintenance Grant — deadline March 15. Here's how to apply", "Yayasan XYZ offering library renovation grants for vernacular schools". **Status: Uncertain** — TF used to have visibility into funding channels but is unsure if current access still exists. Fallback: AI monitors MOE website and state JPN pages for new circulars, same as News Watch monitors media. |

**Exit criteria**: >200 schools verified. AI review handling >50% of routine data changes. WhatsApp channels active in at least 3 states.

### Phase 4: The Asset (Advocacy Engine)

**Duration**: Ongoing
**Dependencies**: Phases 0-3 complete, 12+ months of data

| Deliverable | Description |
|-------------|-------------|
| One-click reports | Generate Ministry/Parliament briefings from live data in <5 minutes |
| Historical trend analysis | Enrolment over time, parliamentary attention over time, cross-year comparisons |
| Annual MOE import pipeline | Automated yearly data refresh from MOE |
| Published MP Scorecard | Annual report on parliamentary attention to Tamil schools |
| Election-ready report cards | During GE/state elections: auto-generate constituency report card (incumbent's scorecard, school stats, trends, at-risk schools) |
| Annual State of Tamil Schools report | Comprehensive annual report combining all data sources |

---

## 8. Cold-Start Strategy

The six tactics that solve the chicken-and-egg problem. Ordered by priority and sequenced for maximum effect.

### Tactic 1: Parliament Watch — Content before contacts

Launch Parliament Watch immediately. Zero contacts needed. Public Hansard data produces high-value intelligence that builds audience organically. Community leaders, journalists, and MPs' offices find the content; schools follow.

### Tactic 2: "Are You on the Map?" — Publish first, collect later

Publish all 528 school profiles on `tamilschool.org.my`. Schools discover themselves via Google search. "Claim This Page" via MOE email collects verified contacts as a byproduct of curiosity and pride.

### Tactic 3: Direct email to 526 schools — Sequenced, not spammed

Send personalised notifications in batches of ~50/day after the map is live and partner endorsements are secured. Each email is a transactional notification about their school, not marketing. Sent from `tamilschool.org.my` with proper DKIM/SPF/DMARC. The 50/day limit is deliberate — it builds sender reputation gradually and avoids spam flags on a new sending domain.

**Sequence**:
1. Weeks 1-2: Launch map + Parliament Watch. Share with 4 partner networks. Build initial buzz.
2. Weeks 3-4: Get endorsements from network leaders. Partner logos on site footer.
3. Weeks 5-8: Email schools in batches of ~50/day. Personalised subject: "Your school's profile on tamilschool.org.my".

**The clerk problem is actually a feature**: The person checking the school email is likely a clerk — but clerks process administrative correspondence. "Your school has a new profile page" is exactly the kind of thing they forward to the headmaster or print for the notice board. A grant deadline alert is something they act on directly.

### Tactic 4: Leverage existing networks — 4 phone calls

TF doesn't need to collect 528 contacts one by one. TF needs to make **4 phone calls**: share the first Parliament Watch report with each network's leadership, ask them to forward to members, include a "Subscribe" link. Contacts build organically. This is not "partnership building" — it's activating relationships that already exist.

| Organisation | Represents | Content angle |
|-------------|------------|---------------|
| LPS Federation | School Boards of Managers | Grant alerts, Parliament Watch |
| Headmasters' association | Tamil school headmasters | Policy updates, MOE circulars, data verification |
| Former students' associations | Alumni | "Are You on the Map?" (pride), Parliament Watch |
| Tamil Teachers Union | Teachers | Teacher-related parliamentary mentions, staffing data |

### Tactic 5: PIBG AGM season play

PIBG AGMs happen annually, roughly the same period across all schools. Every school elects a new committee — new chair, new treasurer, new contact details. This is the single best moment to collect fresh data.

Create a **"PIBG Registration Kit"** with 4 components:
1. AGM agenda template
2. Minutes template
3. TF registration form (QR code linking to online form)
4. One-pager: "What Tamil Foundation can do for your school"

Distribute via LPS Federation and Headmasters' association ahead of AGM season. Schools get something useful; TF gets fresh contacts and updated committee details from hundreds of schools in a 2-3 month window.

### Tactic 6: WhatsApp-first engagement

Create state-level WhatsApp broadcast channels (not groups — channels are one-way, no spam). Share one useful thing per week: a Parliament Watch highlight, a grant alert, an interesting data point from the school map. The channel *is* the contact list. When subscriber counts grow, introduce Magic Links for data verification.

WhatsApp is where Malaysian schools actually communicate. Email is for official MOE correspondence. Engagement happens on WhatsApp.

### Messaging Principle: Pride, Not Data

Frame every interaction around what the school gains (visibility, recognition, resources), never around what TF needs (data).

- "We're building the definitive directory of Tamil schools. We want to make sure yours looks right."
- "Your school's profile has been viewed 47 times this month."
- The headmaster who ignores a survey will respond to "we're featuring your school."

---

## 9. Cost Analysis

### 9.1 Monthly Operating Costs

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| Supabase Free tier (database + auth + storage) | $0 | 500 MB sufficient for 10+ years |
| Cloud Run — backend + pipelines | $0-5 | Scales to zero when idle |
| Cloud Run or Vercel — frontend | $0 | Static generation + SSR |
| Gemini Flash API (Hansard + news + content) | $2-10 | Higher during Parliament sitting periods |
| Email broadcasts (Brevo/Resend free tier) | $0 | 300 emails/day (Brevo) sufficient initially |
| Image/social card generation | $0-5 | Optional, for social media posts |
| **Total** | **$2-20/month** | ~$5-15 typical |

### 9.2 One-Time Costs

| Item | Cost | Notes |
|------|------|-------|
| School image harvest (Google APIs) | ~$5 | 528 schools, existing API key |
| Domain | $0 | Already owned |
| Google Workspace | $0 | Shared with TF |

### 9.3 Annual Cost Estimate

**Year 1**: ~$60-240 (mostly Gemini API during Parliament sitting + Cloud Run)
**Ongoing**: ~$60-180/year

Under RM 1,000/year for an automated intelligence unit + advocacy platform + communications hub.

---

## 10. Success Metrics

### 10.1 Phase 0 Metrics (Parliament Watch)

| KPI | Target | Measurement |
|-----|--------|-------------|
| Reports published per sitting period | 100% of sitting days covered | Count of published reports |
| Time from Hansard PDF to published report | <24 hours | Timestamp comparison |
| Audience reach per report | >500 views within 7 days | Website analytics + social engagement |
| MP Scorecard accuracy | >85% mention classification accuracy | Manual audit of 20 mentions |

### 10.2 Phase 1+ Metrics (Full Platform)

| KPI | Target | Timeline |
|-----|--------|----------|
| School pages live | 528/528 | Phase 1 launch |
| Schools claimed (verified) | >200 (38%) | 6 months post-launch |
| Active subscribers | >500 | 6 months post-launch |
| Broadcast open rate | >50% | Ongoing |
| Data freshness | >80% of schools verified in last 6 months | 12 months post-launch |
| Advocacy speed | Ministry-ready report in <5 minutes | Phase 4 |
| Magic Link verification rate | >60% of recipients confirm data | Ongoing |
| News response time | Response draft within 30 minutes of trigger | Phase 2 |

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Hansard format changes** | Low | Medium | Pipeline uses text extraction, not fixed layout parsing. Adapt extraction logic if PDF structure changes. |
| **AI analysis quality** | Medium | High | Human review gate on all output. Build test set of manually labelled mentions. Iterate prompts based on errors. |
| **Low school claim rate** | Medium | Medium | Multiple acquisition channels (email, networks, WhatsApp, AGM). "Are You on the Map?" creates organic discovery. Value-first approach reduces friction. |
| **Email deliverability** | Medium | Medium | DKIM/SPF/DMARC configured. Batched sends. Transactional (not marketing) framing. Partner endorsements. |
| **Single operator (bus factor)** | High | High | Document all pipelines. Automate everything possible. AI handles production; human handles editorial. System continues producing even if operator changes. |
| **MOE email changes** | Low | Medium | Emails are stable (Google Workspace). Re-import MOE data annually to catch changes. |
| **Scope creep** | Medium | Medium | This PRD defines specific phases. Phase 0 is standalone. Each phase has exit criteria. Do not begin next phase until current phase criteria met. |
| **Community backlash** | Low | High | MP Scorecard may upset some MPs. Position as accountability tool, not attack. Data-backed, factual, non-partisan. Human review prevents inflammatory content. |
| **Parliament YouTube changes** | Medium | Low | Video extraction is a "should" feature, not critical path. Core value is text-based Hansard analysis. |
| **Grant alert access** | Medium | Low | Uncertain whether TF still has access to funding channels. Alternative: AI monitors MOE/JPN websites for circulars. |

---

## 12. Existing Assets

### 12.1 Data Assets

| Asset | Status | Value |
|-------|--------|-------|
| MOE Jan 2026 school list (528 schools) | Ready | Enrolment, teachers, GPS, emails, constituency mapping |
| MOE email addresses (526/528) | Ready | Authentication mechanism for Magic Links |
| GPS verification (476 confirmed + 25 offset) | Ready | 95% of schools confirmed on Google Maps |
| Constituency mapping (122 parl + 222 DUN + 68 PPD) | Ready | Enables hyper-local advocacy pages |
| Historical school board/HM/enrolment data | Various formats | Years of accumulated institutional knowledge |
| Hansard historical corpus (1959-2020) | Available | 3,684 PDFs, 167M words for baseline analysis |

### 12.2 Technical Assets

| Asset | Status |
|-------|--------|
| Google Places API key | Active |
| `verify_school_pins.py` tool | Built and tested |
| `tamilschool.org.my` domain | Owned, Google Workspace configured |
| Cloud Run infrastructure | Running for 3 other TF projects |
| Supabase account | Active, running 3 other projects |

### 12.3 Relationship Assets

| Organisation | Relationship | Relevance |
|-------------|-------------|-----------|
| LPS Federation | Active working relationship | School board access, endorsement |
| Headmasters' association | Active working relationship | School-level access, endorsement |
| Former students' associations | Active working relationship | Amplification, emotional engagement |
| Tamil Teachers Union | Active working relationship | Teacher data, policy monitoring, endorsement |

---

## 13. Dependencies & Assumptions

### Dependencies

| Dependency | Impact if unavailable | Mitigation |
|-----------|----------------------|------------|
| Hansard PDFs remain publicly accessible | Parliament Watch cannot function | PDFs have been public for decades; low risk. Archive copies as downloaded. |
| MOE email addresses remain stable | Authentication mechanism breaks | Re-import MOE data annually. Fallback to manual verification. |
| Google Maps API key remains active | No school images, no map | Existing key, low usage. Budget for paid tier if needed. |
| Partner network endorsement | Slower adoption, weaker credibility | Start with Parliament Watch (no endorsement needed). Build credibility first. |
| TF Admin availability (~10 min/sitting day) | Content cannot be published | Automate as much as possible. Train backup reviewer if available. |

### Assumptions

- Malaysian Parliament continues to publish Hansard as downloadable PDFs
- MOE continues to publish school data annually in Excel format
- Tamil school policy remains a topic of parliamentary discussion
- 528 schools remain roughly stable (closures/mergers offset by new schools)
- Google Workspace continues as MOE's email platform for schools
- TF continues to operate and maintain the platform

---

## 14. Open Questions

| # | Question | Needed From | Impact |
|---|----------|-------------|--------|
| 1 | **HM Council endorsement**: Recent leadership change — is the new president willing to endorse SJK(T) Connect? | TF / direct outreach | Affects partner logos and school outreach credibility |
| 2 | **Grant alert access**: Does TF still have visibility into funding channels (MOE grants, state allocations, CSR programmes)? | TF | Determines whether Tactic 6 is a content pillar or falls back to AI monitoring |
| 3 | **Historical Hansard availability**: Can TF access the full 1959-2020 corpus (3,684 PDFs) for baseline analysis? | Research / open access | Affects historical MP Scorecard depth |
| 4 | **Publishing channel**: Where should Parliament Watch reports initially be published — TF website, dedicated section on tamilschool.org.my, or social media only? | TF | Affects Phase 0 build scope |
| 5 | **Content language**: Should reports be in English only, or English + Tamil + Malay? | TF | Affects content generation pipeline complexity |
| 6 | **Timing**: When does Phase 0 start? Is there a triggering event (next Parliament sitting, Lentera launch, community demand)? | TF / Elan | Affects build priority relative to other projects |
| 7 | **Tamil school names in Tamil**: Do we have Tamil-script school names for all 528 schools, or only English/Malay? | TF / data audit | Affects school page completeness |

---

## 15. Appendices

### A. Constituency Data Summary

| Metric | Count |
|--------|-------|
| Total SJK(T) schools | 528 |
| Parliamentary constituencies with SJK(T)s | 122 (of 222 total) |
| State seats (DUN) with SJK(T)s | 222 |
| Districts (PPD) with SJK(T)s | 68 |
| States with SJK(T)s | 11 |
| Top constituency | Port Dickson (15 schools) |
| Top state | Perak (134 schools, 25% of all SJK(T)s) |
| Schools with MOE email | 526/528 (99.6%) |
| Schools confirmed on Google Maps | 476/529 (90%) |
| Schools near-confirmed on Google Maps | 501/529 (95%) |

### B. Tamil News Sources for Monitoring

| Source | Language | URL | Notes |
|--------|----------|-----|-------|
| Makkal Osai | Tamil | makkalosai.com.my | Largest Tamil daily |
| Malaysiakini Tamil | Tamil | malaysiaindru.my | Malaysiakini's Tamil edition |
| BERNAMA Tamil | Tamil/Malay | bernama.com/tam/ | National wire service |
| MyVelicham | Tamil | myvelicham.com | Online Tamil portal |
| Free Malaysia Today | English | freemalaysiatoday.com | Covers Tamil school stories |
| Malaysiakini | English/Malay | malaysiakini.com | Headlines scrapeable (content paywalled) |
| Google News Alerts | All | alerts.google.com | Free, keyword-based, push to email |

### C. Related Documents

- Project Idea Doc: `Random/tamil_schools/PROJECT-IDEA.md`
- MOE School Data: `Random/tamil_schools/SenaraiSekolahWeb_Januari2026.xlsx`
- GPS Verification: `Random/tamil_schools/school_pin_verification.xlsx`
- Constituency Data: `Random/tamil_schools/பள்ளிகள் - மாநிலம்.xlsx`
- Pin Verification Tool: `Random/tamil_schools/tools/verify_school_pins.py`

### D. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-02-14 | Elan / TF | Initial draft — converted from PROJECT-IDEA.md |
| 0.2 | 2026-02-15 | Elan / TF | Staff engineer review: entity linking (E2a), review UI spec (E8/F6), MentionedSchool bridge table, ephemeral execution model |

---

*End of PRD Draft v0.1*
