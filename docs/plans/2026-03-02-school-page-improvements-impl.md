# School Page Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix data quality (proper case, phone, address), redesign school page layout (side-by-side desktop, compact mobile), add school leadership model, and set up i18n infrastructure.

**Architecture:** Three sprints — Sprint 3.1 (backend data migrations + SchoolLeader model), Sprint 3.2 (frontend layout redesign), Sprint 3.3 (i18n infrastructure). Each sprint is self-contained and deployable.

**Tech Stack:** Django 5.x, Next.js 14, next-intl, Tailwind CSS, PostgreSQL (Supabase)

**Design doc:** `docs/plans/2026-03-02-school-page-improvements-design.md`

---

## Sprint 3.1: Data Quality + SchoolLeader Model — COMPLETED (2026-03-02)

See `docs/retrospective-sprint3.1.md` for details. 41 new tests, 662 backend total.

---

## Sprint 3.2: Frontend Layout Redesign

### Task 8: Update TypeScript Types

**Files:**
- Modify: `frontend/lib/types.ts` (lines 23-45)

**Step 1: Add SchoolLeader type and update SchoolDetail**

```typescript
// Add after SchoolImageData interface (~line 22)
export interface SchoolLeader {
  role: string;
  role_display: string;
  name: string;
}

// Add to SchoolDetail interface:
  leaders: SchoolLeader[];
```

**Step 2: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: add SchoolLeader type to frontend"
```

---

### Task 9: Redesign School Page — Side-by-Side Layout

**Files:**
- Modify: `frontend/app/school/[moe_code]/page.tsx` (lines 77-157)
- Modify: `frontend/components/SchoolProfile.tsx` (entire file)

**Step 1: Write/update frontend tests**

Add tests for:
- Combined student count in stat card (primary + preschool)
- SKM stat card removed
- Full MOE name not rendered
- MOE code not duplicated
- Side-by-side layout has correct grid classes
- SchoolLeader section renders when leaders exist
- SchoolLeader section hidden when no leaders

**Step 2: Restructure page.tsx**

Replace the current layout (lines 77-157) with:

```tsx
return (
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <Breadcrumb items={breadcrumbItems} />

    {/* Hero: Side-by-side on desktop, stacked on mobile */}
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
      {/* Photo — 3/5 width on desktop */}
      <div className="lg:col-span-3">
        <SchoolPhotoGallery
          images={school.images}
          imageUrl={school.image_url}
          schoolName={displayName}
        />
      </div>

      {/* Name + Stats — 2/5 width on desktop */}
      <div className="lg:col-span-2 flex flex-col justify-center space-y-3">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {displayName}
        </h1>
        {school.name_tamil && (
          <p className="text-lg text-gray-700">{school.name_tamil}</p>
        )}
        <p className="text-sm text-gray-500">
          {school.moe_code} · {school.state} · {school.ppd}
        </p>
        <EditSchoolLink moeCode={school.moe_code} />

        {/* Stat cards — compact row */}
        <div className="grid grid-cols-3 gap-3 pt-2">
          <StatCard
            label="Students"
            value={(school.enrolment ?? 0) + (school.preschool_enrolment ?? 0)}
          />
          <StatCard label="Teachers" value={school.teacher_count ?? 0} />
          <StatCard label="Grade" value={school.grade || "—"} />
        </div>
      </div>
    </div>

    {/* Main content */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <SchoolProfile school={school} />
        {/* ... MiniMap, MentionsSection, NewsWatch, SchoolHistory unchanged */}
      </div>
      <div className="space-y-6">
        {/* Sidebar unchanged */}
      </div>
    </div>

    <div className="mt-8">
      <ClaimButton moeCode={school.moe_code} />
    </div>
  </div>
);
```

Remove the full MOE name line (`school.name`) from the header area.

**Step 3: Rewrite SchoolProfile.tsx**

Remove:
- SKM stat card (line 16-19)
- MOE Code detail row (line 28)
- Full Name detail row (line 29)
- Old stat cards section (lines 11-20) — moved to page.tsx

Update:
- Address: use `" "` instead of `", "` between postcode and city
- Assistance Type: map `SBK` → `Government-Aided (SBK)`, `SK` → `Government (SK)`
- Show student breakdown: School, Preschool, Special Needs as separate rows (always, not conditional)

Add:
- School Leadership section (after School Details)

```tsx
{/* School Leadership */}
{school.leaders && school.leaders.length > 0 && (
  <div className="bg-white rounded-lg border border-gray-200 p-6">
    <h2 className="text-lg font-semibold text-gray-800 mb-4">
      School Leadership
    </h2>
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
      {school.leaders.map((leader) => (
        <DetailRow
          key={leader.role}
          label={leader.role_display}
          value={leader.name}
        />
      ))}
    </dl>
  </div>
)}
```

**Step 4: Run frontend tests**

Run: `cd frontend && npm test`

**Step 5: Visual check**

Run: `cd frontend && npm run dev` → check desktop and mobile layouts

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: school page redesign — side-by-side layout, leadership section"
```

---

### Task 10: Update Remaining Frontend Components

**Files:**
- Review and update if state/ppd/name values appear in:
  - `frontend/components/SchoolMarkers.tsx` — info window displays
  - `frontend/components/SearchBox.tsx` — search result display
  - `frontend/components/SchoolTable.tsx` — table rows
  - `frontend/components/ConstituencyList.tsx` — state column
  - `frontend/components/StateFilter.tsx` — state dropdown

Since data is now proper case in the database, these components should display correctly without code changes. **Verify visually** that all pages look right.

**Step 1: Check the state filter dropdown still works**

The state values changed from `PERAK` to `Perak`. The frontend filter passes the state value to the API `?state=` query param. Verify the backend filter is case-insensitive or update it.

Check: `backend/schools/api/views.py` — the state filter. If it uses `filter(state=...)` it needs exact match. If data is now `Perak`, the filter and API must agree.

**Step 2: Run all frontend tests**

Run: `cd frontend && npm test`

**Step 3: Commit any fixes**

---

### Task 11: Sprint 3.2 Close

**Step 1: Run full test suites**

Backend: `cd backend && python -m pytest -q`
Frontend: `cd frontend && npm test`

**Step 2: Update CHANGELOG**

**Step 3: Commit and push**

```bash
git add -A && git commit -m "chore: sprint 3.2 close — school page layout redesign"
git push
```

---

## Sprint 3.3: i18n Infrastructure

### Task 12: Install and Configure next-intl

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/messages/en.json`
- Create: `frontend/messages/ta.json`
- Create: `frontend/i18n/request.ts`
- Create: `frontend/i18n/routing.ts`
- Modify: `frontend/next.config.js`
- Create: `frontend/middleware.ts`

Follow next-intl App Router setup guide. Key steps:

1. `cd frontend && npm install next-intl`
2. Create routing config with `en` and `ta` locales, `en` as default
3. Create middleware for locale detection/redirect
4. Move `app/` pages under `app/[locale]/`
5. Update `layout.tsx` to use locale from params for `<html lang={locale}>`

This is a large structural change. Refer to next-intl docs for exact configuration.

**Commit after setup works with English only (no Tamil translations yet).**

---

### Task 13: Extract English Strings

**Files:**
- Modify: `frontend/messages/en.json`
- Modify: All ~20 component files to use `useTranslations()` hook

Extract the ~140 hardcoded strings into `messages/en.json` organised by component:

```json
{
  "header": {
    "title": "SJK(T) Connect",
    "schoolMap": "School Map",
    "constituencies": "Constituencies",
    "parliamentWatch": "Parliament Watch"
  },
  "schoolProfile": {
    "schoolDetails": "School Details",
    "address": "Address",
    "email": "Email",
    "phone": "Phone",
    "locationType": "Location Type",
    "assistanceType": "Assistance Type",
    "sessions": "Sessions",
    "school": "School",
    "preschool": "Preschool",
    "specialNeeds": "Special Needs",
    "students": "students",
    "schoolLeadership": "School Leadership",
    "politicalRepresentation": "Political Representation",
    "constituency": "Constituency",
    "dun": "DUN"
  }
}
```

Update each component to use `const t = useTranslations("schoolProfile")` and replace hardcoded strings with `t("schoolDetails")`, etc.

**This is tedious but mechanical. Work through components one at a time, test after each.**

---

### Task 14: Tamil Translations

**Files:**
- Modify: `frontend/messages/ta.json`

Translate all ~140 strings to Tamil. Key translations:

```json
{
  "header": {
    "title": "SJK(T) இணைப்பு",
    "schoolMap": "பள்ளி வரைபடம்",
    "constituencies": "தொகுதிகள்",
    "parliamentWatch": "நாடாளுமன்ற கண்காணிப்பு"
  },
  "schoolProfile": {
    "schoolDetails": "பள்ளி விவரங்கள்",
    "address": "முகவரி",
    "students": "மாணவர்கள்"
  }
}
```

**Must follow `tamil-style-guide.md` for all Tamil text.**

---

### Task 15: Language Switcher + Sprint 3.3 Close

**Files:**
- Modify: `frontend/components/Header.tsx` — add language toggle (EN | தமிழ்)
- Run full test suites
- Update CHANGELOG
- Commit and push

---

## Deployment Notes

- Sprint 3.1 requires running `python manage.py migrate` on production after deploying backend
- Sprint 3.2 is frontend-only deploy
- Sprint 3.3 is frontend-only deploy (URL structure changes from `/school/X` to `/en/school/X` — set up redirects)
- Each sprint is independently deployable
