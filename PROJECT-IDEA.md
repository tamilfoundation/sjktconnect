# SJK(T) Connect — Intelligence & Advocacy Hub

**Status:** Parked (concept phase, not in development)
**Date:** 2026-02-13
**Updated:** 2026-02-14
**Owner:** Elan / Tamil Foundation
**Domain:** `tamilschool.org.my` (owned by Tamil Foundation, shares TF's Google Workspace credentials)

---

## Background

Elan has compiled data on ~530 SJK(T) schools in Malaysia over many years, tracking:
- Student population, teacher count, preschool enrolment
- School board members (PIBG)
- Headmasters
- Location (GPS coordinates)
- Contact details, addresses
- School grading and classification (SKM status)

Previously had a full-time staff member updating this data. The project wound down after certain school relocation projects concluded and the data became less immediately useful.

**Core problem:** School data changes constantly (headmasters transfer, boards rotate, enrolment shifts yearly). One person — or even one staff member — cannot keep up. The data is never fully accurate.

**Why a passive directory fails:** Schools are constantly asked for data by various NGOs but rarely receive value in return. They stop responding. A static directory becomes a maintenance burden with no engagement loop.

---

## The Strategic Pivot: "Give-to-Get"

Instead of asking schools for data, **push value first**. The Tamil Foundation acts as the central intelligence node, broadcasting high-value information (funding alerts, policy changes, grant deadlines) to schools. In exchange for this value, schools verify their own data as a side effect.

This transforms the database from a maintenance burden into a **strategic advocacy asset**.

### The Operational Loop

1. **Trigger:** TF acquires high-value info (e.g., "RM 50k Maintenance Grant Guidelines released")
2. **Broadcast:** TF sends an email alert to all registered School Reps
3. **The Gate:** To access the full guide or template, the HM/PIBG clicks a unique Magic Link
4. **Verification:** The link opens a pre-filled form: "Please confirm your current Enrolment and PIBG Chair to proceed"
5. **Reward:** The user confirms (1 click) and gets the resource
6. **Result:** TF gets fresh data; the school gets funding help

### Why this works
- Schools *want* the funding guide — data confirmation is a byproduct, not a chore
- No accounts or passwords (Magic Link access via email)
- 30-second interaction, not a 10-minute wiki edit
- Builds a direct communication channel between TF and every school

---

## User Roles

| Role | Access | Purpose |
|------|--------|---------|
| **TF Admin** | Full view of all schools. Can broadcast, export, manage. | Central operations |
| **School Rep** (HM / PIBG Chair / LPS) | Magic Link access to *their* school only. Can view and confirm/edit. | Data verification |
| **Field Partner** (Phase 3+) | View-only for assigned regions. Can submit "Verified Visit" reports. | On-ground validation |

---

## Features

### A. Intelligence Engine (Backend CRM)

The heart of the system — a CRM for schools.

- **School Profile:** GPS, MOE code, address, board members, headmaster, enrolment history, infrastructure status (verified/unverified tags)
- **Broadcast Tool:** Filter by "All Schools" or "Schools in Perak" or "Schools with <50 Students". Send via email.
- **Audit Trail:** Every change logged (who, when, old value, new value). Essential for advocacy credibility.
- **Annual MOE Import:** Bulk-import official enrolment data yearly to keep baseline fresh without relying on school reps.

### B. Magic Link Updater (School-facing)

No accounts. No passwords. Just a link.

- System generates a secure, time-limited link sent via email
- Mobile-friendly page shows: the resource they requested (top) + pre-filled school data to confirm (bottom)
- Action: [Yes, Confirm] or [No, Edit]

### C. Public Advocacy Map (Public-facing)

A sanitised view for the general public, donors, and parliamentarians.

- Map of all 530 schools (GPS verified — tool already built)
- Filters: "Under-enrolled schools", "Schools needing libraries", by state/district
- Privacy: Hide private phone numbers. Show official school contacts only.
- SEO-friendly: one page per school, findable via Google

### D. AI Review Layer

Gemini-powered review of community submissions and Magic Link edits.

**Three tiers:**
- **Auto-approve:** Low-risk changes (contact info, minor corrections)
- **AI-approve + notify:** Medium-risk (new headmaster, enrolment within reasonable range). Approved but included in weekly digest.
- **Flag for human:** High-risk (school closure, drastic enrolment change, spam)

**Checks:**
- Sanity: Is enrolment plausible? (50 to 55 fine, 50 to 5000 flagged)
- Consistency: 200 students with 1 teacher? Flag.
- Duplicates: Same change submitted twice? Merge.
- GPS corrections: Use Places API to verify (tool already built)
- Spam/abuse: Obvious junk filtered out

### E. Parliament Watch — Automated Hansard Intelligence Pipeline

An AI-powered system that monitors Malaysian parliamentary proceedings (Hansard) for any mention of Tamil schools, analyses the significance, and generates ready-to-publish content — with minimal human involvement.

**This is the first product.** It can run independently before the full platform is built, and it solves the chicken-and-egg problem by producing high-value content that gives schools a reason to subscribe.

#### How it works

1. **Collect:** A scheduled script downloads new Hansard PDFs from [parlimen.gov.my](https://www.parlimen.gov.my/senarai-hansard.html?uweb=dr&lang=en) after each sitting day. PDFs are text-based (no OCR needed). Parliament sits ~70-80 days/year.
2. **Extract:** Pull text from PDFs, identify all passages mentioning Tamil school keywords — "SJK(T)", "sekolah Tamil", "sekolah vernakular", "SJKT", specific school names, etc.
3. **Analyse:** Gemini processes each mention and determines:
   - **Who said it?** Minister, backbencher, opposition? Asking or answering?
   - **What kind of mention?** Budget allocation, oral question, policy statement, throwaway reference, deflection?
   - **Does it matter?** Significant (new commitment, funding figure, policy change) vs routine (passing reference, procedural mention)
   - **What's the sentiment?** Advocating, deflecting, promising, attacking?
   - **What changed?** Compare with previous sittings — new commitment? Broken promise? Reversal?
4. **Score:** Build a longitudinal **MP Tamil School Scorecard** tracking:
   - Which MPs raise Tamil school issues, how often, and how substantively
   - Which ministers answer substantively vs give generic replies
   - Which of the 122 constituencies with Tamil schools have MPs who've *never* mentioned them
   - Parliamentary attention trends over time (increasing or declining?)
   - Constituency-level context: when an MP speaks, automatically link to the schools in their constituency (e.g., "Port Dickson has 15 SJK(T)s — the most in Malaysia")
5. **Generate content:** AI drafts multiple outputs from the same analysis:
   - **Per-sitting brief** (1 page): "Parliament Watch: What was said about Tamil schools today"
   - **Monthly intelligence report** (3-5 pages): Summary, key quotes, MP scorecard update, what to watch
   - **Social media posts**: Quote cards, MP scorecard visuals, short commentary threads
   - **Video clips**: 30-60 second clips from Parliament YouTube with the MP's actual words, timestamped link or extracted clip for direct posting
   - **Broadcast email**: The monthly report becomes the "Intelligence Blast" for subscribers
6. **Extract video clip:** Parliament proceedings are uploaded daily to the [Parlimen Malaysia YouTube channel](https://www.youtube.com/@parlimenmalaysia1) and [RTM Parlimen](https://rtmparlimen.rtm.gov.my/). Using the free [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) library (no API key needed), the system pulls auto-generated captions with timestamps, matches them against the Hansard text to find the exact moment, and generates either a timestamped YouTube link or extracts the 30-60 second clip using yt-dlp. A video clip of an MP actually saying the words — with TF's analysis overlaid — is far more shareable than a text quote. Cost: $0.
7. **Human review:** One person spends ~10 minutes reviewing AI drafts before publishing. The human is the quality gate, not the production line.

#### Why minimal human input is the right design

The traditional model fails because of human bottlenecks:

> Parliament sits → someone watches → writes notes → passes to comms → they draft → approval → published 5 days later → nobody cares

The AI model:

> Parliament sits → PDF published (same/next day) → AI processes in 2 minutes → drafts ready → **one person reviews for 10 minutes** → published

Speed is the entire point of parliamentary monitoring. A response on Tuesday morning to something said on Monday is powerful. A response on Friday is irrelevant.

#### Why this solves the cold-start problem

- **No contacts needed to start.** Hansard is public data. TF can begin producing Parliament Watch reports immediately.
- **Content creates the audience.** Schools, community leaders, and journalists who see these reports will want to subscribe.
- **The MP Scorecard creates accountability.** MPs will know they're being tracked. Community members will share it.
- **Each report is a broadcast opportunity.** "Your MP has never mentioned Tamil schools in Parliament" is a powerful message to send to a school in that constituency.

#### Cost

| Component | Monthly cost |
|-----------|-------------|
| PDF download + text extraction (Python) | Free |
| Gemini Flash for analysis + content generation | ~$2-5 when Parliament is sitting, $0 when not |
| Email broadcasts (Brevo/Resend free tier) | Free |
| Image generation for social cards | $0-5 |
| Cloud Run hosting (scheduled job) | <$1 |
| **Total** | **$3-10/month during sitting periods** |

#### Source data

- Hansard PDFs: [parlimen.gov.my](https://www.parlimen.gov.my/senarai-hansard.html?uweb=dr&lang=en) (open data, public use)
- Historical corpus available: [Malaysian Hansard Corpus 1959-2020](https://www.researchgate.net/publication/351934907_The_Development_of_the_Malaysian_Hansard_Corpus_A_Corpus_of_Parliamentary_Debates_1959-2020) — 3,684 PDFs, 167 million words. Could be used for historical analysis of Tamil school mentions over decades.

### F. News Watch + AI Rapid Response

An extension of Parliament Watch that monitors news media for Tamil school mentions and — critically — **drafts responses, not just reports**. This turns TF from an observer into a rapid-response communications operation, powered by AI.

Parliament Watch is the *sensor* for parliamentary proceedings. News Watch is the *sensor* for media. The Rapid Response layer sits on top of both and generates actionable output.

#### The full pipeline: Watch → Analyse → Respond

**Sensors (two feeds):**

1. **Parliament Watch** — Hansard PDFs (structured, reliable, unique to TF)
2. **News Watch** — media articles across multiple sources and languages

**News sources available online:**

| Source | Language | Type |
|--------|----------|------|
| [Makkal Osai](https://makkalosai.com.my/) | Tamil | Largest Tamil daily, active website |
| [Malaysiakini Tamil](https://malaysiaindru.my/) | Tamil | Malaysiakini's Tamil edition |
| [BERNAMA Tamil](https://www.bernama.com/tam/) | Tamil/Malay | National wire service |
| [MyVelicham](https://www.myvelicham.com/) | Tamil | Online Tamil news portal |
| [Free Malaysia Today](https://www.freemalaysiatoday.com/) | English | Covers Tamil school stories regularly |
| [Malaysiakini](https://www.malaysiakini.com/) | English/Malay | Headlines scrapeable (content paywalled) |
| Google News Alerts | All languages | Free, keyword-based, push to email |

**Simplest sensor:** Google News Alerts for "SJK(T)" + "sekolah Tamil" + "Tamil school Malaysia". Free, zero scraping, catches stories across all outlets and languages. When an alert fires, AI fetches the article, analyses it, and drafts a response.

**Note:** Most Tamil school news originates in *Malay-language* sources (MOE announcements, Hansard, state education circulars) and *English* media. Tamil media covers it but is rarely the primary source. The monitoring must be multilingual.

#### AI Rapid Response — the action layer

The response layer generates output appropriate to what was detected:

| Trigger | AI generates |
|---------|-------------|
| Minister announces school maintenance fund, Tamil schools not mentioned | Press statement: "528 Tamil schools ask — are we included?" + infographic showing maintenance needs |
| News article about a specific Tamil school closure | Data-backed response: school's enrolment history, list of other at-risk schools, TF's position + social post |
| MP raises teacher shortage in Parliament | Amplification: quote card + TF commentary + teacher-student ratios across all 528 schools |
| Negative story (e.g., school mismanagement) | Contextual response: enrolment trends, funding history, systemic factors — not just reaction |
| Budget day | Same-day analysis: "What Budget 2027 means for Tamil schools" with allocation breakdown |
| MOE policy circular affecting vernacular schools | Plain-language explainer for schools + recommended actions + broadcast to subscribers |

**Output formats per trigger:**
- Press statement / official TF response (for media pickup)
- Social media posts (quote cards, infographics, commentary threads)
- Broadcast email to subscribers (Intelligence Blast)
- Data-backed one-pager (for MPs, journalists, donors)
- Talking points (for TF spokesperson or allies)

#### Why this matters: TF has no comms team

TF is essentially one person. The traditional model requires a research officer, a writer, a designer, and an approver — and even then, responses come days late.

The AI model:

> Trigger detected → AI analyses in 2 minutes → drafts full response package (statement + social posts + data sheet) → **one person reviews for 10 minutes** → published

One person with AI operates at the speed and output quality of a full communications department. The human role is editorial judgement (tone, timing, what to publish and what to hold), not production.

#### Combined cost (Parliament Watch + News Watch + Rapid Response)

| Component | Monthly cost |
|-----------|-------------|
| Parliament Watch (Hansard pipeline) | $3-10 during sitting |
| News Watch (Google Alerts + optional scraping) | $0-2 |
| AI analysis + response drafting (Gemini Flash) | $2-5 |
| Social media card generation | $0-5 |
| **Total** | **$5-15/month when active** |

Under $20/month for an automated intelligence unit + communications department.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js | Public map + school pages + Magic Link forms |
| Backend | Django REST | Admin CRM, broadcast engine, AI review pipeline |
| Database | Supabase (PostgreSQL) | Golden Record of schools + audit log + RLS |
| AI | Gemini API | Review logic for submissions |
| Email | Resend or Brevo (free tier) | Broadcasts + Magic Links. Start here. |
| WhatsApp | Defer to Phase 3+ | WhatsApp Business API costs ~RM 0.20-0.40/msg |
| Hosting | Cloud Run | Same as other TF projects |

---

## Existing Assets

- **Domain:** `tamilschool.org.my` — owned by Tamil Foundation. Perfect home for the public school map and school pages.
- `SKM Distance.xlsx` — 529 schools with coordinates, enrolment, codes, distance matrix
- `SenaraiSekolahWeb_Januari2026.xlsx` — Official MOE school list (Jan 2026) with 528 Tamil schools, including email addresses (526/528 have `@moe.edu.my`), phone, fax, enrolment, teacher count, GPS, parliamentary constituency, DUN, SKM status
- **Constituency mapping (already complete):** Every school mapped to parliamentary constituency (122 constituencies), state seat / DUN (222 seats), district / PPD (68 districts), and state (11 states). Enables hyper-local advocacy: constituency report cards, MP scorecards, district comparisons, election-time analysis. Top constituency: Port Dickson (15 schools). Top state: Perak (134 schools, 25% of all SJK(T)s)
- `school_pin_verification.xlsx` — GPS verification results (476 confirmed, 25 offset, 28 not on Google Maps)
- `tools/verify_school_pins.py` — Pin verification tool (reusable for GPS change submissions)
- Years of accumulated school board, headmaster, and enrolment data (various formats)
- Google Places API key (already set up)
- **School building images (ready to harvest):** 501 of 529 schools (95%) are confirmed or near-confirmed on Google Maps. Images can be sourced via:
  1. Google Places Photos — real user-uploaded photos (best quality, varies by school)
  2. Google Street View Static API — road-level photo of school building (~70-80% coverage, depends on rural access)
  3. Google Maps Static Satellite — bird's-eye view (100% coverage, always available as fallback)
  - One-time cost: under $5 for all 528 schools using existing GPS coordinates and API key
  - Tool: extend `verify_school_pins.py` or create `harvest_school_images.py`
- **Existing relationships:** Working relationships with LPS Federation, Headmasters' association, Former students' associations, and Tamil Teachers Union — all four key stakeholder networks

---

## Success Metrics

| KPI | Target |
|-----|--------|
| Data freshness | >80% of schools verified in last 6 months |
| Broadcast engagement | >50% open rate on intelligence alerts |
| Advocacy speed | Generate a Ministry-ready report in <5 minutes |
| Verification rate | >60% of Magic Link recipients confirm their data |

---

## Roadmap

### Phase 0: Parliament Watch (Standalone — can start immediately)
- Build Hansard scanner + AI analysis pipeline
- Generate first Parliament Watch reports from current and recent sittings
- Run historical analysis on past Hansards to establish MP Scorecard baseline
- Publish reports on TF website/social media — no subscriber list needed
- *Value:* Immediate content, immediate credibility, builds audience organically
- *Solves:* The chicken-and-egg problem. This is TF's first product.

### Phase 1: The Seed (Database + Public Map)
- Import existing Excel data into Supabase
- Public read-only map and school pages ("Are You on the Map?" campaign)
- **Constituency pages:** Auto-generated page for each of 122 parliamentary constituencies and 222 DUN seats — listing schools, aggregate stats, MP/ADUN name, Parliament Watch score. SEO-friendly URLs: `tamilschool.org.my/constituency/port-dickson`
- Admin dashboard for TF
- Parliament Watch reports link to relevant constituency and school pages
- Direct email outreach to all 526 schools (batched over 2-3 weeks, endorsed by partner networks)
- *Value:* TF can generate advocacy reports immediately. 122 constituency pages = 122 pieces of ready-made content

### Phase 2: The Value (Broadcasts + Magic Links)
- Email broadcast tool with audience filters
- Magic Link verification flow
- Parliament Watch monthly report becomes the flagship broadcast
- First "Intelligence Blast" sent to contacts acquired via Phase 0 and 1
- *Value:* Proves the give-to-get model works

### Phase 3: The Platform (Scale + Partners)
- AI reviewer for submissions
- Field Partner role (view-only, verified visits)
- WhatsApp broadcast channels (state-level)
- Weekly digest emails
- *Value:* Self-sustaining data loop

### Phase 4: The Asset (Advocacy Engine)
- One-click report generation for Ministry/Parliament briefings
- Historical trend analysis (enrolment over time, parliamentary attention over time)
- AI-assisted news monitoring (flag policy changes affecting schools)
- Annual MOE bulk import pipeline
- MP Scorecard becomes a published annual report
- **Election-ready constituency report cards** — during GE/state elections, auto-generate "Tamil School Report Card" for every constituency: incumbent's scorecard, school stats, trends, at-risk schools
- *Value:* TF becomes the authoritative voice on SJK(T) data

---

## Pre-Build Checklist

### For Phase 0 (Parliament Watch) — low barrier, can start now

1. **Feasibility:** Can the Hansard PDF pipeline be built and tested? (Yes — PDFs are public, text-based, predictable URL pattern.)
2. **Content quality:** Does the AI analysis produce genuinely useful intelligence? (Build a prototype, run it against 5 recent Hansards, evaluate output quality.)
3. **Publishing channel:** Where do reports go initially? (TF website, social media, email list — even a small one.)
4. **Human reviewer:** Who spends 10 minutes per sitting day reviewing AI drafts before publishing?

### For Phase 1+ (Full Platform) — higher commitment

1. **Content pipeline:** Can TF produce at least 1 high-value broadcast per month for 12 months? (Parliament Watch alone may cover 6-8 months. Supplement with grant alerts, MOE announcements, policy changes.)
2. **Contact list:** Does TF have email addresses for HMs/PIBG at most schools? (If not, Phase 0 audience-building and Phase 1 "Are You on the Map?" campaign are the collection mechanisms.)
3. **Trigger:** What event would justify starting the full platform? (Lentera launch, community demand, funding secured, Parliament Watch audience reaches critical mass, or simply "it's time"?)

---

## Cold-Start Strategy

The original chicken-and-egg problem: *Why should schools give contact info without value? Why produce content without an audience?*

**Resolution:** Parliament Watch breaks the deadlock. It requires zero contacts, zero school participation, and zero infrastructure beyond a script and an AI model. It produces high-value, time-sensitive content from public data. The audience builds itself — community leaders, journalists, MPs' offices, and eventually schools. By the time Phase 1 launches, TF already has an audience, a reputation, and content to broadcast.

### Tactic 1: "Are You on the Map?" — Publish first, collect later

Publish the public school map using existing MOE data. All 528 schools, with whatever info is already available. Schools will Google themselves, find their page, and come to TF to correct or claim it.

**Claim mechanism — MOE email as authentication:**

The Jan 2026 MOE dataset includes official email addresses for 526 of 528 Tamil schools. The pattern is `[SCHOOL_CODE]@moe.edu.my` (e.g., `JBD0050@moe.edu.my`). These are Google Workspace accounts, actively used.

The claim flow:
1. Visitor lands on a school page → sees public profile (name, location, enrolment, district)
2. Clicks **"Are you from this school? Claim this page."**
3. Enters their email address
4. System checks: if it matches the `@moe.edu.my` address on file → sends a Magic Link instantly
5. Recipient clicks Magic Link → lands on page with edit access → reviews/corrects data
6. If email doesn't match → "Please use your school's official MOE email"

**Why this works:**
- No passwords, no accounts, no registration forms — just email verification
- The MOE email *is* the authentication. If you can access `JBD0050@moe.edu.my`, you're someone authorised at that school
- We already have all 526 emails — no data collection needed
- When headmasters transfer, the new HM inherits the school email account — so the mechanism stays valid automatically
- Google Workspace means the inbox is actively monitored — Magic Links won't rot

**Downloadable School Profile Card:** Each school page includes a "Download as PDF" button — a printable one-page profile card with the school's name, location map, enrolment, district, and key stats. Headmasters can print and pin it on their notice board. A beautiful, tangible artefact that says "your school matters" is worth more than a hundred emails asking for data.

**No contacts needed to launch.** The map goes live, schools discover themselves, and the claim flow collects verified contacts as a byproduct.

### Tactic 1b: Direct email outreach to all 526 schools

Since TF has all 526 `@moe.edu.my` addresses, schools can be emailed directly once the map is live. But this must be sequenced carefully — not a cold blast.

**Sequence:**
1. **Weeks 1-2:** Launch map + Parliament Watch on `tamilschool.org.my`. Share with 4 partner networks. Build initial buzz.
2. **Weeks 3-4:** Get endorsement from network leaders. Their logos appear on the site footer.
3. **Weeks 5-8:** Email schools in batches of ~50/day (builds sender reputation, avoids spam flags). Not a marketing blast — a *personalised notification*:

> Subject: Your school's profile on tamilschool.org.my
>
> Kepada pihak SJK(T) Sri Gading,
>
> Tamil Foundation has created a public profile page for your school on tamilschool.org.my, endorsed by [Tamil Teachers Union / LPS Federation / HM Council].
>
> Your page includes: location map, school photo, enrolment data, and key statistics.
>
> **[View your school's page →]**
>
> Is the information accurate? Click "Claim this page" to verify and edit.
>
> Every month, we also send a Parliament Watch report on what's being said about Tamil schools in Parliament.

**Why this isn't spam:**
- It's a transactional notification about *their* school, not a marketing pitch
- Sent from `tamilschool.org.my` with proper DKIM/SPF/DMARC (shares Tamil Foundation's Google Workspace credentials)
- Endorsed by organisations the school recognises (logos in the email)
- Contains genuinely useful content (their own school profile + Parliament Watch)

**The clerk problem is actually a feature:** The person checking the school email is likely a clerk — but clerks process administrative correspondence. "Your school has a new profile page" is exactly the kind of thing they forward to the headmaster or print for the notice board. A grant deadline alert is something they act on directly.

### Tactic 2: Leverage existing networks — TF already has the relationships

There is no national or state-level PIBG federation for Tamil schools. But four key organisations exist, and **TF has a working relationship with all of them:**

| Organisation | Who they represent | What they offer SJK(T) Connect |
|-------------|-------------------|-------------------------------|
| **LPS Federation** (Lembaga Pengurus Sekolah) | School Boards of Managers | Direct access to school management. LPS members handle infrastructure, funding applications, school affairs. Most interested in grant alerts and Parliament Watch. |
| **Headmasters' association** | Tamil school headmasters | The people who control the `@moe.edu.my` inboxes. Interested in policy updates, MOE circulars, data verification. |
| **Former students' associations** | Tamil school alumni | Emotional connection to schools. Would share content virally. Good amplifiers for "Are You on the Map?" and Parliament Watch. |
| **Tamil Teachers Union** | Tamil school teachers | Interested in teacher-related parliamentary mentions, staffing data, policy changes. |

**What this means:** TF doesn't need to collect 528 contacts one by one. TF needs to make 4 phone calls:
1. Share the first Parliament Watch report with each network's leadership
2. Ask them to forward it to their members
3. Include a "Subscribe for monthly updates" link in the report
4. Contacts build organically from there

**Each network serves a different content angle:**
- Parliament Watch → all four networks (everyone cares what's said in Parliament)
- Grant/funding alerts → LPS Federation + Headmasters
- Policy/circular explainers → Headmasters + Teachers Union
- "Are You on the Map?" → Former students (pride/nostalgia) + Headmasters (accuracy)

**Partner logos on the site:** `tamilschool.org.my` footer displays logos of supporting organisations — Tamil Teachers Union, LPS Federation, and potentially HM Council (pending — recent leadership change, relationship needs re-confirming). This gives the site instant credibility when schools receive the notification email.

This is not "partnership building" — it's activating relationships that already exist.

### Tactic 3: Start with 20 schools

Pick 20 schools where TF already has personal relationships — from relocation projects, Lentera pilot planning, or through the networks above. Call the headmaster directly. "We're building something for Tamil schools. Can we feature your school first?"

Those 20 become proof of concept, testimonials, and case studies. When approaching the next 50, you say "here's what SJK(T) Ladang Rini's headmaster said about it."

### Tactic 4: WhatsApp-first — skip email at the start

Create state-level WhatsApp broadcast channels (not groups — channels are one-way, no spam). Share one useful thing per week: a Parliament Watch highlight, a grant alert, an interesting data point from the school map.

The channel *is* the contact list. When subscriber counts grow, introduce Magic Links for data verification.

WhatsApp is where Malaysian schools actually communicate. Email is for official MOE correspondence. Engagement happens on WhatsApp.

### Tactic 5: PIBG AGM season play

PIBG AGMs happen annually, roughly the same period across all schools. Every school elects a new committee — new chair, new treasurer, new contact details. This is the single best moment to collect fresh data.

TF creates a **"PIBG Registration Kit"**:
- AGM agenda template
- Minutes template
- TF registration form (QR code linking to a quick online form)
- One-pager: "What Tamil Foundation can do for your school"

Distribute through the LPS Federation and Headmasters' association ahead of AGM season. Schools get something useful; TF gets fresh contacts and updated committee details for hundreds of schools in a 2-3 month window.

### Tactic 6: Grant & funding alert service

Schools miss funding opportunities because nobody tells them in time. MOE maintenance grants, state allocations, corporate CSR programmes, Yayasan-linked funds — these come and go, often with tight deadlines. If TF curates just one useful funding alert per month, that alone justifies subscribing.

**Content examples:**
- "RM 50k Maintenance Grant — deadline March 15. Here's how to apply." + application template
- "Yayasan XYZ offering library renovation grants for vernacular schools. Eligibility: enrolment under 150."
- "State allocation for school IT equipment announced. Here's what your school is entitled to."

**Status: Uncertain.** TF used to have visibility into these funding channels but is unsure if current access still exists. Needs to be verified before committing to this as a content pillar. If direct access has lapsed, alternative sources include:
- MOE website announcements and circulars
- State education department (JPN) notices
- Parliament Watch itself (budget allocations are debated in Hansard)
- LPS Federation and Headmasters' association contacts (they hear about grants through their own networks)

**Even without direct access:** AI can monitor MOE's website and state JPN pages for new circulars, the same way News Watch monitors media. When a relevant circular appears, AI drafts a plain-language explainer + action steps + deadline reminder for broadcast.

**This is the second content pillar alongside Parliament Watch.** Parliament Watch tells schools what's being *said* about them. Grant alerts tell schools what's *available* to them. Together, they make the subscription indispensable.

### Messaging principle: Pride, not data

This is not a standalone tactic but the tone that runs through all communications. Nobody wants to "update a database." Everyone wants their school to be *seen*.

- "Tamil Foundation is building the definitive directory of Tamil schools in Malaysia. Every school will have its own page. We want to make sure yours looks right." — This is a dignity pitch, not a data collection exercise.
- "Your school's profile has been viewed 47 times this month" — Visibility creates motivation to keep data current.
- The headmaster who ignores a survey will respond to "we're featuring your school."

Frame every interaction around what the school gains (visibility, recognition, access to resources), never around what TF needs (data).

---

## Decision

**Phase 0 (Parliament Watch):** Ready to prototype. Low cost (~$5/month), no dependencies on contacts or school participation. Could be built in 1-2 sessions and tested against recent Hansards.

**Phase 1+ (Full Platform):** Revisit when:
- Parliament Watch has been running for 2-3 months and has built an audience
- Lentera programme needs school data (natural trigger)
- TF secures funding or a partner for the build
- Community interest surfaces organically
- Or Elan decides "it's time"
