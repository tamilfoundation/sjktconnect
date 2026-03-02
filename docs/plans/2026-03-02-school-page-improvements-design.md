# Design: SJK(T) Connect — School Page Improvements

**Date:** 2026-03-02
**Status:** Approved

## Overview

A set of data quality, layout, and structural improvements to the school profile page. Also introduces i18n infrastructure and a school leadership directory.

## 1. Proper Case (Database Migration)

One-time data migration that title-cases all text fields stored in ALL CAPS from the MOE import.

**Fields affected:**
- `short_name`: `SJK(T) LADANG SUNGAI RAYA` → `SJK(T) Ladang Sungai Raya`
- `name`: `SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG SUNGAI RAYA` → `Sekolah Jenis Kebangsaan (Tamil) Ladang Sungai Raya`
- `state`: `KEDAH` → `Kedah`, `NEGERI SEMBILAN` → `Negeri Sembilan`
- `ppd`: `PPD LANGKAWI` → `PPD Langkawi`, `PPW SENTUL` → `PPW Sentul`
- `address`: `JALAN AYER HANGAT` → `Jalan Ayer Hangat`
- `city`: `LANGKAWI` → `Langkawi`
- `email`: `KBD6019@moe.edu.my` → `kbd6019@moe.edu.my`

**Abbreviations kept uppercase:** `SJK(T)`, `PPD`, `PPW`, `JPN`, `LDG`, `SG`, `KG`, `JLN`, `D/A`, `H/D`, Roman numerals (`II`, `III`)

**Apostrophe handling:** `DATO'` → `Dato'`, `SAINT MARY'S` → `Saint Mary's`

**Import script update:** `make_short_name()` updated so future MOE re-imports produce proper case.

## 2. Phone Number Standardisation (Database Migration)

**Current:** Raw MOE data like `049663429`
**Target:** `+60-4 966 3429`

**Rules:**
- Strip leading `0`, prefix with `+60-`
- Area code grouping: 1 digit for single-digit area codes (3, 4, 5, 6, 7, 9), 2 digits for others (82–89)
- Remaining digits grouped in blocks of 3–4
- Stored formatted in the database
- Malformed numbers logged for manual review

## 3. Address Cleanup (Database Migration)

- Remove comma between postcode and city: `07000, LANGKAWI` → `07000 Langkawi`
- Proper case applied (covered in Section 1)
- Extra spaces trimmed

## 4. School Page Layout Redesign

### Desktop — Side-by-Side Hero

```
┌──────────────────────────────────────────────────┐
│  Home / Kedah / SJK(T) Ladang Sungai Raya       │
│                                                  │
│  ┌──────────────────┐                            │
│  │                  │  SJK(T) Ladang Sungai Raya │
│  │  School Photo    │  KBD6019 · Kedah           │
│  │  (~60% width)    │  PPD Langkawi              │
│  │                  │                            │
│  │                  │  ┌─────┬─────┬─────┐       │
│  │                  │  │ 104 │  13 │  C  │       │
│  └──────────────────┘  │ Stu │ Tea │ Grd │       │
│   [thumb] [thumb]      └─────┴─────┴─────┘       │
│                                                  │
│  ┌─ School Details ────────────────────────────┐ │
│  │ Address:  Jalan Ayer Hangat, Ladang Sungai  │ │
│  │           Raya, 07000 Langkawi, Kedah       │ │
│  │ Email:    kbd6019@moe.edu.my                │ │
│  │ Phone:    +60-4 966 3429                    │ │
│  │ Type:     Government-Aided (SBK) · Bandar   │ │
│  │ Sessions: 1 (Pagi Sahaja)                   │ │
│  │ School:   81 students                       │ │
│  │ Preschool: 23 students                      │ │
│  │ Special Needs: 0 students                   │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Mobile — Compact Stacked Layout

Photo full-width but constrained aspect ratio. Name, subtitle, and stat cards use tight spacing. School Details uses a compact list — no wasted whitespace.

### Removed from Display
- Full MOE name (`SEKOLAH JENIS KEBANGSAAN (TAMIL)...`) — redundant with short_name heading
- MOE Code from School Details — already in subtitle
- SKM stat card — Grade tells the story (Grade C schools are invariably SKM)

### Stat Cards
- **Students**: primary + preschool combined (104 = 81 + 23)
- **Teachers**: unchanged
- **Grade**: unchanged
- SKM removed

### Label Improvements
- `SBK` → `Government-Aided (SBK)`
- `SK` → `Government (SK)`

## 5. School Leadership Contacts

### New Model: `SchoolLeader`

| Field | Type | Notes |
|-------|------|-------|
| school | ForeignKey → School | |
| role | CharField (choices) | `board_chair`, `headmaster`, `pta_chair`, `alumni_chair` |
| name | CharField | Person's name |
| phone | CharField (blank) | Private — admin only |
| email | EmailField (blank) | Private — admin only |
| is_active | BooleanField | Default true |

### Display Order
1. Board Chairman (Pengerusi Lembaga)
2. Headmaster (Guru Besar)
3. PTA Chairman (Pengerusi PIBG)
4. Alumni Association Chairman (Pengerusi Persatuan Bekas Murid) — only if exists

### Privacy
- Public API returns name and role only
- Phone and email never exposed via API
- Django admin inline for full contact management

### UI
Section hidden entirely if no leaders recorded. Individual rows hidden if role is empty.

## 6. i18n Infrastructure

### Approach: `next-intl` with URL Prefix Routing

- Routes: `/en/school/ABD2164`, `/ta/school/ABD2164`
- ~140 UI strings extracted into `messages/en.json` and `messages/ta.json`
- Language switcher in header
- Dates/numbers formatted per locale
- Default language: English (redirect `/` → `/en/`)

## Shelved
- **School badge** — deferred to future sprint (TF data ~30% coverage, needs upload flow)

## Change Summary

| # | Change | Layer |
|---|--------|-------|
| 1 | Proper case all text fields | Database migration |
| 2 | Lowercase emails | Database migration |
| 3 | Standardise phone format | Database migration |
| 4 | Address cleanup (postcode/city comma) | Database migration + frontend |
| 5 | Desktop side-by-side layout | Frontend |
| 6 | Mobile compact layout | Frontend |
| 7 | Remove full MOE name | Frontend |
| 8 | Remove duplicate MOE code | Frontend |
| 9 | Remove SKM stat card | Frontend |
| 10 | Combined student count in stat card | Frontend |
| 11 | Separate student breakdowns in details | Frontend |
| 12 | Expand SBK/SK labels | Frontend |
| 13 | School Leadership model + UI | Backend + Frontend |
| 14 | i18n infrastructure (next-intl) | Frontend |
