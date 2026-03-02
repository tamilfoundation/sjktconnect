# i18n Infrastructure Implementation Plan (Sprint 3.3)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add trilingual support (EN/TA/MS) to the SJK(T) Connect Next.js frontend using next-intl, with locale-prefixed URLs and a language switcher.

**Architecture:** Install next-intl, move all pages under `app/[locale]/`, create middleware for locale detection/redirect, extract ~162 hardcoded strings into JSON message files, translate to Tamil and Malay, add language switcher to Header.

**Tech Stack:** Next.js 14, next-intl, TypeScript, Tailwind CSS

---

## Task 1: Install next-intl and create routing config

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/i18n/routing.ts`
- Create: `frontend/i18n/request.ts`
- Modify: `frontend/next.config.js`

**Step 1: Install next-intl**

Run: `cd frontend && npm install next-intl`

**Step 2: Create routing config**

Create `frontend/i18n/routing.ts`:

```typescript
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en", "ta", "ms"],
  defaultLocale: "en",
});
```

**Step 3: Create request config**

Create `frontend/i18n/request.ts`:

```typescript
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  // Ensure the locale is valid
  if (!locale || !routing.locales.includes(locale as any)) {
    locale = routing.defaultLocale;
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
```

**Step 4: Update next.config.js**

Replace `frontend/next.config.js` with:

```javascript
const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

module.exports = withNextIntl(nextConfig);
```

**Step 5: Create skeleton message files**

Create `frontend/messages/en.json`:
```json
{
  "common": {
    "home": "Home",
    "loading": "Loading..."
  }
}
```

Create `frontend/messages/ta.json`:
```json
{
  "common": {
    "home": "முகப்பு",
    "loading": "ஏற்றுகிறது..."
  }
}
```

Create `frontend/messages/ms.json`:
```json
{
  "common": {
    "home": "Utama",
    "loading": "Memuatkan..."
  }
}
```

**Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/i18n/ frontend/next.config.js frontend/messages/
git commit -m "feat: install next-intl and create i18n routing config"
```

---

## Task 2: Create middleware and move pages under [locale]

**Files:**
- Create: `frontend/middleware.ts`
- Move: All 17 files from `frontend/app/` into `frontend/app/[locale]/`
- Modify: `frontend/app/[locale]/layout.tsx` (updated from `app/layout.tsx`)

**Step 1: Create middleware**

Create `frontend/middleware.ts`:

```typescript
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Match all pathnames except for:
  // - API routes, _next, _vercel
  // - Files with extensions (favicon.ico, images, etc.)
  matcher: "/((?!api|trpc|_next|_vercel|.*\\..*).*)",
};
```

**Step 2: Move all pages under [locale]**

Create `frontend/app/[locale]/` directory. Move these files/folders:

```bash
cd frontend
mkdir -p app/\[locale\]
# Move all page directories and files (NOT globals.css)
mv app/page.tsx app/\[locale\]/
mv app/layout.tsx app/\[locale\]/
mv app/school app/\[locale\]/
mv app/constituencies app/\[locale\]/
mv app/constituency app/\[locale\]/
mv app/dun app/\[locale\]/
mv app/parliament-watch app/\[locale\]/
mv app/claim app/\[locale\]/
mv app/subscribe app/\[locale\]/
mv app/unsubscribe app/\[locale\]/
mv app/preferences app/\[locale\]/
```

`globals.css` stays at `app/globals.css`.

**Step 3: Update layout.tsx for locale**

Update `frontend/app/[locale]/layout.tsx`:

```typescript
import type { Metadata } from "next";
import "../globals.css";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "SJK(T) Connect — Tamil School Intelligence Platform",
  description:
    "Interactive map and data platform for Malaysia's 528 Tamil schools. Track parliamentary mentions, MP scorecards, and school data.",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  const { locale } = params;

  // Validate locale
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }

  // Get messages for the current locale
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="flex flex-col min-h-screen bg-gray-50">
        <NextIntlClientProvider messages={messages}>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

**Step 4: Verify the dev server starts**

Run: `cd frontend && npm run dev`

Visit `http://localhost:3000` — should redirect to `http://localhost:3000/en`.
Visit `http://localhost:3000/en/school/ABC1234` — should load school page.

**Step 5: Commit**

```bash
git add frontend/middleware.ts frontend/app/
git commit -m "feat: move pages under [locale] with next-intl middleware"
```

---

## Task 3: Extract English strings — Header, Footer, common

**Files:**
- Modify: `frontend/messages/en.json`
- Modify: `frontend/messages/ta.json`
- Modify: `frontend/messages/ms.json`
- Modify: `frontend/components/Header.tsx`
- Modify: `frontend/components/Footer.tsx`

**Step 1: Add header/footer/common strings to en.json**

Update `frontend/messages/en.json` (replace entire file):

```json
{
  "common": {
    "home": "Home",
    "loading": "Loading...",
    "back": "Back",
    "retry": "Retry",
    "cancel": "Cancel",
    "save": "Save",
    "noResults": "No results found",
    "students": "students",
    "schools": "schools",
    "na": "N/A",
    "mapUnavailable": "Map unavailable",
    "noBoundaryData": "No boundary data available"
  },
  "header": {
    "title": "SJK(T) Connect",
    "schoolMap": "School Map",
    "constituencies": "Constituencies",
    "parliamentWatch": "Parliament Watch",
    "toggleMenu": "Toggle menu"
  },
  "footer": {
    "copyright": "© {year} Tamil Foundation Malaysia. Data from MOE & Parliament of Malaysia.",
    "subscribe": "Subscribe to Intelligence Blast"
  }
}
```

**Step 2: Add Tamil translations**

Update `frontend/messages/ta.json`:

```json
{
  "common": {
    "home": "முகப்பு",
    "loading": "ஏற்றுகிறது...",
    "back": "பின்",
    "retry": "மீண்டும் முயற்சி",
    "cancel": "ரத்து",
    "save": "சேமி",
    "noResults": "முடிவுகள் எதுவும் கிடைக்கவில்லை",
    "students": "மாணவர்கள்",
    "schools": "பள்ளிகள்",
    "na": "தகவல் இல்லை",
    "mapUnavailable": "வரைபடம் கிடைக்கவில்லை",
    "noBoundaryData": "எல்லைத் தரவு கிடைக்கவில்லை"
  },
  "header": {
    "title": "SJK(T) இணைப்பு",
    "schoolMap": "பள்ளி வரைபடம்",
    "constituencies": "தொகுதிகள்",
    "parliamentWatch": "நாடாளுமன்றக் கண்காணிப்பு",
    "toggleMenu": "பட்டியலை மாற்று"
  },
  "footer": {
    "copyright": "© {year} தமிழ் அறக்கட்டளை மலேசியா. தரவு: கல்வி அமைச்சு & மலேசிய நாடாளுமன்றம்.",
    "subscribe": "புலனாய்வுச் செய்திமடலுக்குப் பதிவு"
  }
}
```

**Step 3: Add Malay translations**

Update `frontend/messages/ms.json`:

```json
{
  "common": {
    "home": "Utama",
    "loading": "Memuatkan...",
    "back": "Kembali",
    "retry": "Cuba semula",
    "cancel": "Batal",
    "save": "Simpan",
    "noResults": "Tiada hasil ditemui",
    "students": "murid",
    "schools": "sekolah",
    "na": "T/A",
    "mapUnavailable": "Peta tidak tersedia",
    "noBoundaryData": "Data sempadan tidak tersedia"
  },
  "header": {
    "title": "SJK(T) Connect",
    "schoolMap": "Peta Sekolah",
    "constituencies": "Kawasan Parlimen",
    "parliamentWatch": "Pemantauan Parlimen",
    "toggleMenu": "Togol menu"
  },
  "footer": {
    "copyright": "© {year} Tamil Foundation Malaysia. Data daripada KPM & Parlimen Malaysia.",
    "subscribe": "Langgan Surat Perisikan"
  }
}
```

**Step 4: Update Header.tsx to use translations**

Replace `frontend/components/Header.tsx`:

```typescript
"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useState } from "react";
import LanguageSwitcher from "./LanguageSwitcher";

export default function Header() {
  const t = useTranslations("header");
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 relative z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary-700">
              {t("title")}
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link
              href="/"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("schoolMap")}
            </Link>
            <Link
              href="/constituencies"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("constituencies")}
            </Link>
            <Link
              href="/parliament-watch"
              className="text-sm font-medium text-gray-700 hover:text-primary-600"
            >
              {t("parliamentWatch")}
            </Link>
            <LanguageSwitcher />
          </nav>

          <button
            className="md:hidden p-2 text-gray-600 hover:text-gray-900"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={t("toggleMenu")}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="md:hidden bg-white border-t border-gray-200 py-2">
          <Link
            href="/"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("schoolMap")}
          </Link>
          <Link
            href="/constituencies"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("constituencies")}
          </Link>
          <Link
            href="/parliament-watch"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setMenuOpen(false)}
          >
            {t("parliamentWatch")}
          </Link>
          <div className="px-4 py-2">
            <LanguageSwitcher />
          </div>
        </div>
      )}
    </header>
  );
}
```

**Step 5: Update Footer.tsx to use translations**

Replace `frontend/components/Footer.tsx`:

```typescript
"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function Footer() {
  const t = useTranslations("footer");

  return (
    <footer className="bg-white border-t border-gray-200 py-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-gray-500">
            {t("copyright", { year: new Date().getFullYear() })}
          </p>
          <Link
            href="/subscribe"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            {t("subscribe")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
```

**Step 6: Create navigation helper**

Create `frontend/i18n/navigation.ts`:

```typescript
import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter } =
  createNavigation(routing);
```

**Step 7: Verify Header and Footer render with translations**

Run: `cd frontend && npm run dev`
Visit `http://localhost:3000/en` — Header should show English nav links.

**Step 8: Commit**

```bash
git add frontend/messages/ frontend/components/Header.tsx frontend/components/Footer.tsx frontend/i18n/navigation.ts
git commit -m "feat: extract Header and Footer strings to i18n message files"
```

---

## Task 4: Create Language Switcher component

**Files:**
- Create: `frontend/components/LanguageSwitcher.tsx`
- Test: `frontend/__tests__/components/LanguageSwitcher.test.tsx`

**Step 1: Write the test**

Create `frontend/__tests__/components/LanguageSwitcher.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

// Mock next-intl
jest.mock("next-intl", () => ({
  useLocale: () => "en",
}));

// Mock i18n navigation
jest.mock("@/i18n/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace: jest.fn() }),
  Link: ({ children, ...props }: any) => <a {...props}>{children}</a>,
}));

describe("LanguageSwitcher", () => {
  it("renders all three locale options", () => {
    render(<LanguageSwitcher />);
    expect(screen.getByText("EN")).toBeInTheDocument();
    expect(screen.getByText("தமிழ்")).toBeInTheDocument();
    expect(screen.getByText("BM")).toBeInTheDocument();
  });

  it("highlights the active locale", () => {
    render(<LanguageSwitcher />);
    const enLink = screen.getByText("EN");
    expect(enLink).toHaveClass("font-bold");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest __tests__/components/LanguageSwitcher.test.tsx --no-cache`
Expected: FAIL (module not found)

**Step 3: Implement LanguageSwitcher**

Create `frontend/components/LanguageSwitcher.tsx`:

```typescript
"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

const localeLabels: Record<string, string> = {
  en: "EN",
  ta: "தமிழ்",
  ms: "BM",
};

export default function LanguageSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  function onLocaleChange(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  return (
    <div className="flex items-center gap-1 text-sm">
      {routing.locales.map((l, i) => (
        <span key={l}>
          {i > 0 && <span className="text-gray-300 mx-1">|</span>}
          <button
            onClick={() => onLocaleChange(l)}
            className={`hover:text-primary-600 ${
              locale === l
                ? "font-bold text-primary-700 underline underline-offset-4"
                : "text-gray-500"
            }`}
          >
            {localeLabels[l]}
          </button>
        </span>
      ))}
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest __tests__/components/LanguageSwitcher.test.tsx --no-cache`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/components/LanguageSwitcher.tsx frontend/__tests__/components/LanguageSwitcher.test.tsx
git commit -m "feat: add LanguageSwitcher component with EN/TA/MS toggle"
```

---

## Task 5: Extract strings — School page + SchoolProfile + StatCard

**Files:**
- Modify: `frontend/messages/en.json` (add `schoolProfile` namespace)
- Modify: `frontend/messages/ta.json`
- Modify: `frontend/messages/ms.json`
- Modify: `frontend/app/[locale]/school/[moe_code]/page.tsx`
- Modify: `frontend/components/SchoolProfile.tsx`

**Step 1: Add schoolProfile strings to all three message files**

Add to `en.json`:

```json
"schoolProfile": {
  "schoolDetails": "School Details",
  "tamilName": "Tamil Name",
  "address": "Address",
  "email": "Email",
  "phone": "Phone",
  "locationType": "Location Type",
  "assistanceType": "Assistance Type",
  "sessions": "Sessions",
  "school": "School",
  "preschool": "Preschool",
  "specialNeeds": "Special Needs",
  "studentsCount": "{count} students",
  "schoolLeadership": "School Leadership",
  "politicalRepresentation": "Political Representation",
  "constituency": "Constituency",
  "dun": "DUN",
  "governmentAided": "Government-Aided (SBK)",
  "government": "Government (SK)",
  "location": "Location",
  "studentsLabel": "Students",
  "teachersLabel": "Teachers",
  "gradeLabel": "Grade",
  "notFound": "School Not Found",
  "notFoundTitle": "School Not Found — SJK(T) Connect",
  "notFoundDescription": "The school you're looking for doesn't exist or may have been removed.",
  "backToMap": "Back to School Map"
},
"metadata": {
  "siteTitle": "SJK(T) Connect",
  "siteName": "SJK(T) Connect",
  "siteDescription": "Interactive map and data platform for Malaysia's 528 Tamil schools. Track parliamentary mentions, MP scorecards, and school data.",
  "schoolTitle": "{name} — SJK(T) Connect",
  "schoolDescription": "{name} ({code}) in {state}. Enrolment: {enrolment} students, {teachers} teachers. Grade {grade}."
}
```

Add to `ta.json`:

```json
"schoolProfile": {
  "schoolDetails": "பள்ளி விவரங்கள்",
  "tamilName": "தமிழ்ப் பெயர்",
  "address": "முகவரி",
  "email": "மின்னஞ்சல்",
  "phone": "தொலைபேசி",
  "locationType": "இட வகை",
  "assistanceType": "உதவி வகை",
  "sessions": "அமர்வுகள்",
  "school": "பள்ளி",
  "preschool": "பாலர் பள்ளி",
  "specialNeeds": "சிறப்புக் கல்வி",
  "studentsCount": "{count} மாணவர்கள்",
  "schoolLeadership": "பள்ளித் தலைமை",
  "politicalRepresentation": "அரசியல் பிரதிநிதித்துவம்",
  "constituency": "தொகுதி",
  "dun": "DUN",
  "governmentAided": "அரசு உதவி (SBK)",
  "government": "அரசு (SK)",
  "location": "இடம்",
  "studentsLabel": "மாணவர்கள்",
  "teachersLabel": "ஆசிரியர்கள்",
  "gradeLabel": "கிரேடு",
  "notFound": "பள்ளி கிடைக்கவில்லை",
  "notFoundTitle": "பள்ளி கிடைக்கவில்லை — SJK(T) இணைப்பு",
  "notFoundDescription": "நீங்கள் தேடும் பள்ளி இல்லை அல்லது நீக்கப்பட்டிருக்கலாம்.",
  "backToMap": "பள்ளி வரைபடத்திற்குத் திரும்பு"
},
"metadata": {
  "siteTitle": "SJK(T) இணைப்பு",
  "siteName": "SJK(T) இணைப்பு",
  "siteDescription": "மலேசியாவின் 528 தமிழ்ப் பள்ளிகளுக்கான தரவுத் தளம். நாடாளுமன்றக் குறிப்புகள், எம்.பி. மதிப்பீடுகள், பள்ளித் தரவு.",
  "schoolTitle": "{name} — SJK(T) இணைப்பு",
  "schoolDescription": "{name} ({code}), {state}. மாணவர் எண்ணிக்கை: {enrolment}, ஆசிரியர்கள்: {teachers}. கிரேடு {grade}."
}
```

Add to `ms.json`:

```json
"schoolProfile": {
  "schoolDetails": "Butiran Sekolah",
  "tamilName": "Nama Tamil",
  "address": "Alamat",
  "email": "E-mel",
  "phone": "Telefon",
  "locationType": "Jenis Lokasi",
  "assistanceType": "Jenis Bantuan",
  "sessions": "Sesi",
  "school": "Sekolah",
  "preschool": "Prasekolah",
  "specialNeeds": "Pendidikan Khas",
  "studentsCount": "{count} murid",
  "schoolLeadership": "Kepimpinan Sekolah",
  "politicalRepresentation": "Perwakilan Politik",
  "constituency": "Kawasan Parlimen",
  "dun": "DUN",
  "governmentAided": "Bantuan Kerajaan (SBK)",
  "government": "Kerajaan (SK)",
  "location": "Lokasi",
  "studentsLabel": "Murid",
  "teachersLabel": "Guru",
  "gradeLabel": "Gred",
  "notFound": "Sekolah Tidak Ditemui",
  "notFoundTitle": "Sekolah Tidak Ditemui — SJK(T) Connect",
  "notFoundDescription": "Sekolah yang anda cari tidak wujud atau mungkin telah dialih keluar.",
  "backToMap": "Kembali ke Peta Sekolah"
},
"metadata": {
  "siteTitle": "SJK(T) Connect",
  "siteName": "SJK(T) Connect",
  "siteDescription": "Platform data interaktif untuk 528 sekolah Tamil di Malaysia. Pantau sebutan parlimen, kad skor MP, dan data sekolah.",
  "schoolTitle": "{name} — SJK(T) Connect",
  "schoolDescription": "{name} ({code}) di {state}. Enrolmen: {enrolment} murid, {teachers} guru. Gred {grade}."
}
```

**Step 2: Update SchoolProfile.tsx to use translations**

Add `"use client"` directive and `useTranslations`:

```typescript
"use client";

import { useTranslations } from "next-intl";
import { SchoolDetail } from "@/lib/types";

interface SchoolProfileProps {
  school: SchoolDetail;
}

export default function SchoolProfile({ school }: SchoolProfileProps) {
  const t = useTranslations("schoolProfile");

  function formatAssistanceType(value: string): string {
    if (value === "SBK") return t("governmentAided");
    if (value === "SK") return t("government");
    return value;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          {t("schoolDetails")}
        </h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {school.name_tamil && (
            <DetailRow label={t("tamilName")} value={school.name_tamil} />
          )}
          <DetailRow
            label={t("address")}
            value={
              [school.address, `${school.postcode} ${school.city}`, school.state]
                .filter(Boolean)
                .join(", ") || "—"
            }
          />
          {school.email && <DetailRow label={t("email")} value={school.email} />}
          {school.phone && <DetailRow label={t("phone")} value={school.phone} />}
          <DetailRow label={t("locationType")} value={school.location_type || "—"} />
          <DetailRow
            label={t("assistanceType")}
            value={formatAssistanceType(school.assistance_type) || "—"}
          />
          <DetailRow
            label={t("sessions")}
            value={
              school.session_count
                ? `${school.session_count} (${school.session_type || "—"})`
                : "—"
            }
          />
          <DetailRow
            label={t("school")}
            value={t("studentsCount", { count: school.enrolment ?? 0 })}
          />
          <DetailRow
            label={t("preschool")}
            value={t("studentsCount", { count: school.preschool_enrolment ?? 0 })}
          />
          <DetailRow
            label={t("specialNeeds")}
            value={t("studentsCount", { count: school.special_enrolment ?? 0 })}
          />
        </dl>
      </div>

      {school.leaders && school.leaders.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            {t("schoolLeadership")}
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

      {school.constituency_code && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            {t("politicalRepresentation")}
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
            <DetailRow
              label={t("constituency")}
              value={
                school.constituency_name
                  ? `${school.constituency_code} ${school.constituency_name}`
                  : school.constituency_code
              }
            />
            {school.dun_name && (
              <DetailRow
                label={t("dun")}
                value={
                  school.dun_code
                    ? `${school.dun_code} ${school.dun_name}`
                    : school.dun_name
                }
              />
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-gray-800 font-medium mt-0.5">{value}</dd>
    </div>
  );
}
```

**Step 3: Update school page to use translations for StatCard labels and breadcrumbs**

In `frontend/app/[locale]/school/[moe_code]/page.tsx`, update the hardcoded strings:
- `"Home"` → use `getTranslations("common")` then `t("home")`
- `"Students"` / `"Teachers"` / `"Grade"` → use `getTranslations("schoolProfile")` then `t("studentsLabel")` etc.
- `"Location"` → `t("location")`

Since this is a Server Component, use `getTranslations` from `next-intl/server` instead of the client hook:

```typescript
import { getTranslations } from "next-intl/server";

// Inside the component function:
const t = await getTranslations("schoolProfile");
const tc = await getTranslations("common");

// Breadcrumbs
const breadcrumbItems = [
  { label: tc("home"), href: "/" },
  { label: school.state, href: `/?state=${encodeURIComponent(school.state)}` },
  { label: displayName },
];

// StatCards
<StatCard label={t("studentsLabel")} value={...} />
<StatCard label={t("teachersLabel")} value={...} />
<StatCard label={t("gradeLabel")} value={...} />

// Location heading
<h2 ...>{t("location")}</h2>
```

Also update `not-found.tsx` in the same directory.

**Step 4: Verify school page renders in English**

Run: `cd frontend && npm run dev`
Visit `http://localhost:3000/en/school/ABC1234` (use a real school code).

**Step 5: Commit**

```bash
git add frontend/messages/ frontend/components/SchoolProfile.tsx frontend/app/
git commit -m "feat: extract school page and SchoolProfile strings to i18n"
```

---

## Task 6: Extract strings — Map components (SchoolMap, SchoolMarkers, SearchBox, StateFilter)

**Files:**
- Modify: `frontend/messages/en.json` (add `home` namespace)
- Modify: `frontend/messages/ta.json`
- Modify: `frontend/messages/ms.json`
- Modify: `frontend/components/SchoolMap.tsx`
- Modify: `frontend/components/SchoolMarkers.tsx`
- Modify: `frontend/components/SearchBox.tsx`
- Modify: `frontend/components/StateFilter.tsx`

**Step 1: Add home namespace strings to all three message files**

Add to `en.json`:

```json
"home": {
  "apiKeyRequired": "Google Maps API Key Required",
  "apiKeyInstructions": "Set NEXT_PUBLIC_GOOGLE_MAPS_API_KEY in your .env.local file.",
  "loadingSchools": "Loading 528 schools...",
  "failedToLoad": "Failed to load schools",
  "searchPlaceholder": "Search schools or constituencies...",
  "searchLabel": "Search schools",
  "clearSearch": "Clear search",
  "schoolsCount": "Schools ({count})",
  "constituenciesCount": "Constituencies ({count})",
  "viewArrow": "View →",
  "filterByState": "Filter by State",
  "allStates": "All States",
  "showingSchools": "Showing {count} of {total} schools",
  "code": "Code:",
  "state": "State:",
  "enrolment": "Enrolment:",
  "teachers": "Teachers:",
  "constituencyLabel": "Constituency:",
  "viewSchool": "View School →"
}
```

Add equivalent `ta.json` and `ms.json` entries (same pattern as previous tasks).

Tamil `home` namespace:

```json
"home": {
  "apiKeyRequired": "Google Maps API விசை தேவை",
  "apiKeyInstructions": ".env.local கோப்பில் NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ஐ அமைக்கவும்.",
  "loadingSchools": "528 பள்ளிகளை ஏற்றுகிறது...",
  "failedToLoad": "பள்ளிகளை ஏற்ற இயலவில்லை",
  "searchPlaceholder": "பள்ளிகள் அல்லது தொகுதிகளைத் தேடு...",
  "searchLabel": "பள்ளிகளைத் தேடு",
  "clearSearch": "தேடலை அழி",
  "schoolsCount": "பள்ளிகள் ({count})",
  "constituenciesCount": "தொகுதிகள் ({count})",
  "viewArrow": "பார் →",
  "filterByState": "மாநிலம் வடிகட்டு",
  "allStates": "அனைத்து மாநிலங்கள்",
  "showingSchools": "{total} பள்ளிகளில் {count} காட்டப்படுகிறது",
  "code": "குறியீடு:",
  "state": "மாநிலம்:",
  "enrolment": "மாணவர் எண்ணிக்கை:",
  "teachers": "ஆசிரியர்கள்:",
  "constituencyLabel": "தொகுதி:",
  "viewSchool": "பள்ளியைப் பார் →"
}
```

Malay `home` namespace:

```json
"home": {
  "apiKeyRequired": "Kunci API Google Maps Diperlukan",
  "apiKeyInstructions": "Tetapkan NEXT_PUBLIC_GOOGLE_MAPS_API_KEY dalam fail .env.local anda.",
  "loadingSchools": "Memuatkan 528 sekolah...",
  "failedToLoad": "Gagal memuatkan sekolah",
  "searchPlaceholder": "Cari sekolah atau kawasan parlimen...",
  "searchLabel": "Cari sekolah",
  "clearSearch": "Padam carian",
  "schoolsCount": "Sekolah ({count})",
  "constituenciesCount": "Kawasan Parlimen ({count})",
  "viewArrow": "Lihat →",
  "filterByState": "Tapis mengikut Negeri",
  "allStates": "Semua Negeri",
  "showingSchools": "Menunjukkan {count} daripada {total} sekolah",
  "code": "Kod:",
  "state": "Negeri:",
  "enrolment": "Enrolmen:",
  "teachers": "Guru:",
  "constituencyLabel": "Kawasan Parlimen:",
  "viewSchool": "Lihat Sekolah →"
}
```

**Step 2: Update each component**

For each of SchoolMap.tsx, SchoolMarkers.tsx, SearchBox.tsx, StateFilter.tsx:
1. Add `useTranslations("home")` hook
2. Replace hardcoded strings with `t("key")` calls
3. For Link components, import from `@/i18n/navigation` instead of `next/link`

**Step 3: Verify map page renders**

Run: `cd frontend && npm run dev`
Visit `http://localhost:3000/en` — map should load with English labels.

**Step 4: Commit**

```bash
git add frontend/messages/ frontend/components/SchoolMap.tsx frontend/components/SchoolMarkers.tsx frontend/components/SearchBox.tsx frontend/components/StateFilter.tsx
git commit -m "feat: extract map component strings to i18n"
```

---

## Task 7: Extract strings — Constituency + DUN pages

**Files:**
- Modify: `frontend/messages/{en,ta,ms}.json` (add `constituency` namespace)
- Modify: `frontend/app/[locale]/constituencies/page.tsx`
- Modify: `frontend/app/[locale]/constituency/[code]/page.tsx`
- Modify: `frontend/app/[locale]/dun/[id]/page.tsx`
- Modify: `frontend/components/ConstituencyList.tsx`
- Modify: `frontend/components/ConstituencySchools.tsx`
- Modify: `frontend/components/ScorecardCard.tsx`
- Modify: `frontend/components/DemographicsCard.tsx`
- Modify: `frontend/components/SchoolTable.tsx`
- Modify: `frontend/components/BoundaryMap.tsx`

**Step 1: Add constituency namespace to all three message files**

Add to `en.json`:

```json
"constituency": {
  "title": "Constituencies",
  "pageTitle": "Constituencies — SJK(T) Connect",
  "pageDescription": "Browse all 222 parliamentary constituencies with Tamil schools in Malaysia. See MP details, school counts, and scorecards.",
  "countSubtitle": "{count} parliamentary constituencies with Tamil schools",
  "notFoundTitle": "Constituency Not Found — SJK(T) Connect",
  "mp": "MP:",
  "adun": "ADUN:",
  "parliament": "Parliament:",
  "tamilSchools": "Tamil Schools",
  "totalStudents": "Total Students",
  "totalTeachers": "Total Teachers",
  "duns": "DUNs",
  "boundary": "Boundary",
  "stateConstituencies": "State Constituencies (DUN)",
  "parliamentConstituency": "Parliament Constituency",
  "dunNotFoundTitle": "DUN Not Found — SJK(T) Connect",
  "allStates": "All States",
  "filterByState": "Filter by state",
  "showingConstituencies": "Showing {count} constituencies · {total} Tamil schools",
  "codeCol": "Code",
  "constituencyCol": "Constituency",
  "stateCol": "State",
  "mpCol": "MP",
  "partyCol": "Party",
  "schoolsCol": "Schools",
  "schoolCol": "School",
  "studentsCol": "Students",
  "teachersCol": "Teachers",
  "ppdCol": "PPD",
  "noSchools": "No Tamil schools found in this area.",
  "schoolsIn": "Schools in {name}",
  "scorecardTitle": "Parliament Watch Scorecard",
  "noActivity": "No parliamentary activity recorded for {name} yet.",
  "totalMentions": "Total Mentions",
  "substantive": "Substantive",
  "questionsAsked": "Questions Asked",
  "commitments": "Commitments",
  "lastMention": "Last mention:",
  "demographics": "Demographics",
  "indianPopulation": "Indian Population",
  "indianPercent": "Indian %",
  "avgIncome": "Avg. Income",
  "povertyRate": "Poverty Rate",
  "giniIndex": "Gini Index",
  "unemployment": "Unemployment"
}
```

Add equivalent Tamil and Malay translations (following same patterns as earlier tasks).

**Step 2: Update each component and page**

For Server Components (page files): use `getTranslations` from `next-intl/server`.
For Client Components: use `useTranslations` hook.
Replace `next/link` with `@/i18n/navigation` Link where internal links exist.

**Step 3: Verify constituency pages render**

Run: `cd frontend && npm run dev`
Visit `http://localhost:3000/en/constituencies` and `http://localhost:3000/en/constituency/P001`.

**Step 4: Commit**

```bash
git add frontend/messages/ frontend/app/\[locale\]/constituencies/ frontend/app/\[locale\]/constituency/ frontend/app/\[locale\]/dun/ frontend/components/ConstituencyList.tsx frontend/components/ConstituencySchools.tsx frontend/components/ScorecardCard.tsx frontend/components/DemographicsCard.tsx frontend/components/SchoolTable.tsx frontend/components/BoundaryMap.tsx
git commit -m "feat: extract constituency and DUN page strings to i18n"
```

---

## Task 8: Extract strings — Claim + Edit + Subscribe + Unsubscribe + Preferences pages

**Files:**
- Modify: `frontend/messages/{en,ta,ms}.json` (add `claim`, `schoolEdit`, `subscribe` namespaces)
- Modify: `frontend/components/ClaimButton.tsx`
- Modify: `frontend/components/ClaimForm.tsx`
- Modify: `frontend/components/SchoolEditForm.tsx`
- Modify: `frontend/components/EditSchoolLink.tsx`
- Modify: `frontend/components/SubscribeForm.tsx`
- Modify: `frontend/components/UnsubscribeConfirmation.tsx`
- Modify: `frontend/components/PreferencesForm.tsx`
- Modify: `frontend/app/[locale]/claim/page.tsx`
- Modify: `frontend/app/[locale]/claim/verify/[token]/page.tsx`
- Modify: `frontend/app/[locale]/school/[moe_code]/edit/page.tsx`
- Modify: `frontend/app/[locale]/subscribe/page.tsx`
- Modify: `frontend/app/[locale]/unsubscribe/[token]/page.tsx`
- Modify: `frontend/app/[locale]/preferences/[token]/page.tsx`

**Step 1: Add claim namespace to en.json**

```json
"claim": {
  "title": "Claim Your School",
  "pageDescription": "Verify and update your Tamil school's information on SJK(T) Connect. Requires a valid @moe.edu.my email address.",
  "intro": "Enter your school's official MOE email address to verify your identity. We'll send you a link to confirm and manage your school's page.",
  "howItWorks": "How it works",
  "step1": "Enter your school's @moe.edu.my email address",
  "step2": "Check your inbox for the verification link",
  "step3": "Click the link to verify your identity",
  "step4": "You can then confirm or update your school's information",
  "verifying": "Verifying your email...",
  "verificationFailed": "Verification Failed",
  "tryAgain": "Try Again",
  "emailVerified": "Email Verified!",
  "linkedTo": "You are now linked to",
  "signedInAs": "Signed in as",
  "goToSchool": "Go to Your School Page",
  "verificationError": "Verification failed.",
  "areYouFromSchool": "Are you from this school?",
  "verifyAndUpdate": "Verify and update your school's information to keep it accurate.",
  "claimThisPage": "Claim This Page",
  "requiresMoeEmail": "Requires a valid @moe.edu.my email address",
  "checkEmail": "Check your email",
  "sentVerification": "We've sent a verification link to",
  "for": "for",
  "linkExpires": "The link expires in 24 hours. Check your spam folder if you don't see it.",
  "schoolEmail": "School email address",
  "emailPlaceholder": "schoolcode@moe.edu.my",
  "moeOnly": "Only @moe.edu.my email addresses are accepted.",
  "somethingWrong": "Something went wrong.",
  "sending": "Sending...",
  "sendVerification": "Send Verification Link"
}
```

**Step 2: Add schoolEdit namespace to en.json**

```json
"schoolEdit": {
  "officialName": "Official Name (MOE)",
  "shortName": "Short Name",
  "state": "State",
  "nameTamil": "Name (Tamil)",
  "address": "Address",
  "postcode": "Postcode",
  "city": "City",
  "email": "Email",
  "phone": "Phone",
  "fax": "Fax",
  "studentEnrolment": "Student Enrolment",
  "preschoolEnrolment": "Preschool Enrolment",
  "specialEnrolment": "Special Education Enrolment",
  "teacherCount": "Teacher Count",
  "sessionsPerDay": "Sessions Per Day",
  "sessionType": "Session Type",
  "readOnly": "(read-only)",
  "isCorrect": "Is this information correct?",
  "confirmOrEdit": "Click \"Confirm\" if all data is accurate, or edit below to make changes.",
  "confirming": "Confirming...",
  "confirmData": "Confirm Data",
  "lastVerified": "Last verified:",
  "by": "by",
  "noChanges": "No changes to save.",
  "failedConfirm": "Failed to confirm.",
  "failedSave": "Failed to save.",
  "changesSaved": "Changes saved and data verified.",
  "saving": "Saving...",
  "saveChanges": "Save Changes",
  "editTitle": "Edit School Data",
  "editBreadcrumb": "Edit",
  "onlyYourSchool": "You can only edit your own school.",
  "failedToLoad": "Failed to load school data.",
  "accessDenied": "Access Denied",
  "backToSchool": "Back to School Page"
}
```

**Step 3: Add subscribe namespace to en.json**

```json
"subscribe": {
  "title": "Subscribe",
  "heading": "Subscribe to Intelligence Blast",
  "intro": "Stay informed about Malaysia's 528 Tamil schools. Receive parliamentary analysis, news alerts, and monthly intelligence digests.",
  "whatYouReceive": "What you'll receive",
  "parliamentWatch": "Parliament Watch",
  "parliamentDesc": "Analysis of Tamil school mentions in parliamentary debates",
  "newsWatch": "News Watch",
  "newsDesc": "Media monitoring alerts about Tamil schools",
  "monthlyBlast": "Monthly Intelligence Blast",
  "monthlyDesc": "Monthly digest of all Tamil school intelligence",
  "monthlyDescAlt": "Comprehensive monthly intelligence digest",
  "youreSubscribed": "You're subscribed!",
  "confirmSent": "A confirmation email has been sent to",
  "manageNote": "You can manage your preferences or unsubscribe at any time using the links in our emails.",
  "emailLabel": "Email address",
  "emailPlaceholder": "your@email.com",
  "nameLabel": "Name",
  "namePlaceholder": "Your name",
  "orgLabel": "Organisation",
  "orgPlaceholder": "Your organisation (optional)",
  "updatesOn": "You'll receive updates on:",
  "allEnabled": "All categories are enabled by default. You can change these after subscribing.",
  "subscribing": "Subscribing...",
  "subscribeButton": "Subscribe",
  "unsubscribeTitle": "Unsubscribe",
  "processing": "Processing your request...",
  "unableTo": "Unable to unsubscribe",
  "linkExpired": "This link may have expired or already been used. Please contact us if you need help.",
  "unsubscribed": "Unsubscribed",
  "removedFrom": "has been removed from all SJK(T) Connect mailings.",
  "changedMind": "Changed your mind?",
  "resubscribe": "Re-subscribe here",
  "preferencesTitle": "Manage Preferences",
  "subscriptionPrefs": "Subscription Preferences",
  "chooseTypes": "Choose which types of intelligence you'd like to receive.",
  "loadingPrefs": "Loading preferences...",
  "unableToLoad": "Unable to load preferences",
  "prefLinkExpired": "This link may have expired. Please use the link from your most recent email.",
  "managingFor": "Managing preferences for",
  "prefsSaved": "Preferences saved successfully.",
  "savingPrefs": "Saving...",
  "savePrefs": "Save Preferences",
  "stopAll": "Want to stop all emails?",
  "unsubscribeAll": "Unsubscribe from all",
  "somethingWrong": "Something went wrong.",
  "whenMps": "— when MPs discuss Tamil schools in Parliament",
  "mediaAlerts": "— media coverage affecting Tamil schools",
  "monthlyDigest": "— comprehensive monthly intelligence digest",
  "parliamentWatchDesc": "— analysis of Tamil school mentions in parliamentary debates",
  "newsWatchDesc": "— media monitoring alerts about Tamil schools"
}
```

**Step 4: Add Tamil and Malay translations for all three namespaces**

Follow the same pattern. For Tamil, follow `tamil-style-guide.md`. For Malay, use standard formal Malay.

**Step 5: Update all components and pages**

For each component:
1. Add `useTranslations("claim")` / `useTranslations("schoolEdit")` / `useTranslations("subscribe")` as appropriate
2. Replace hardcoded strings with `t("key")` calls
3. Replace `next/link` with `@/i18n/navigation` Link

**Step 6: Verify all pages render**

Run: `cd frontend && npm run dev`
Test each page: `/en/claim`, `/en/subscribe`, `/en/preferences/test`.

**Step 7: Commit**

```bash
git add frontend/messages/ frontend/components/ frontend/app/
git commit -m "feat: extract claim, edit, and subscribe page strings to i18n"
```

---

## Task 9: Extract strings — Parliament Watch, Mentions, News, History

**Files:**
- Modify: `frontend/messages/{en,ta,ms}.json` (add `parliamentWatch` namespace entries)
- Modify: `frontend/app/[locale]/parliament-watch/page.tsx`
- Modify: `frontend/components/MentionsSection.tsx`
- Modify: `frontend/components/NewsWatchSection.tsx`
- Modify: `frontend/components/SchoolHistory.tsx`
- Modify: `frontend/components/SchoolImage.tsx`
- Modify: `frontend/components/MiniMap.tsx`

**Step 1: Add parliamentWatch namespace**

Add to `en.json`:

```json
"parliamentWatch": {
  "title": "Parliament Watch — SJK(T) Connect",
  "heading": "Parliament Watch",
  "intro": "Tracking how Malaysian MPs discuss Tamil schools in Parliament. AI-powered analysis of Hansard proceedings with MP scorecards.",
  "comingSoon": "Coming Soon",
  "comingSoonBody": "Parliament Watch reports are currently available on the admin portal. Public access will be enabled in a future update. In the meantime, explore the",
  "schoolMap": "school map",
  "and": "and",
  "constituencyPages": "constituency pages",
  "noMentions": "No parliamentary mentions found for this school yet.",
  "significance": "Significance: {score}/5",
  "newsWatchHeading": "News Watch",
  "noNews": "No news articles yet.",
  "urgent": "Urgent",
  "historyHeading": "History & Story",
  "historyIntro": "Every Tamil school has a story worth telling. Help us preserve it.",
  "historyBody": "If you have information about this school's history — founding year, key milestones, notable alumni — we'd love to hear from you.",
  "contactUs": "Contact us to contribute →",
  "noPhoto": "No photo available. Know this school? Help us by sharing a photo.",
  "photoCredit": "Photo:",
  "editSchoolData": "Edit School Data"
}
```

Add Tamil and Malay equivalents.

**Step 2: Update each component with useTranslations**

Same pattern as previous tasks.

**Step 3: Verify**

Run dev server, visit parliament-watch and school pages with mentions/news.

**Step 4: Commit**

```bash
git add frontend/messages/ frontend/components/ frontend/app/
git commit -m "feat: extract parliament watch, news, and history strings to i18n"
```

---

## Task 10: Update all internal Link imports

**Files:**
- Modify: All component files that use `import Link from "next/link"`

**Step 1: Find all files using next/link**

Run: `grep -rn "from \"next/link\"" frontend/components/ frontend/app/`

**Step 2: Replace with i18n navigation Link**

For every component/page file that uses internal links (not external URLs), change:

```typescript
// Before
import Link from "next/link";

// After
import { Link } from "@/i18n/navigation";
```

This ensures all `<Link href="/school/X">` calls automatically include the locale prefix.

**Exception**: Server Components (page files) that don't use client-side Link can keep using `next/link` if they construct the full locale path themselves, but using `@/i18n/navigation` is simpler and consistent.

**Step 3: Verify navigation works**

Run dev server, click links between pages — all should stay in the current locale.

**Step 4: Commit**

```bash
git add frontend/components/ frontend/app/
git commit -m "refactor: replace next/link with i18n-aware Link across all components"
```

---

## Task 11: Update existing tests

**Files:**
- Modify: All test files in `frontend/__tests__/`

**Step 1: List existing tests**

Run: `find frontend/__tests__ -name "*.test.*" -type f`

**Step 2: Add next-intl mocks to test setup**

Create or update `frontend/__tests__/setup.ts` (or `jest.setup.js`) to mock next-intl globally:

```typescript
// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: (namespace: string) => {
    return (key: string, values?: Record<string, any>) => {
      // Return the key as-is for testing, with values interpolated
      if (values) {
        let result = key;
        Object.entries(values).forEach(([k, v]) => {
          result = result.replace(`{${k}}`, String(v));
        });
        return result;
      }
      return key;
    };
  },
  useLocale: () => "en",
  NextIntlClientProvider: ({ children }: any) => children,
}));

// Mock i18n navigation
jest.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>{children}</a>
  ),
  usePathname: () => "/",
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
  redirect: jest.fn(),
}));
```

**Step 3: Update tests that check for specific text**

Tests that use `getByText("School Details")` will now need `getByText("schoolDetails")` since the mock returns the key. Alternatively, load real English messages in test setup for more realistic tests.

Better approach — load real messages:

```typescript
import en from "../messages/en.json";

jest.mock("next-intl", () => {
  const messages = require("../messages/en.json");
  return {
    useTranslations: (namespace: string) => {
      const ns = messages[namespace] || {};
      return (key: string, values?: Record<string, any>) => {
        let result = ns[key] || key;
        if (values) {
          Object.entries(values).forEach(([k, v]) => {
            result = result.replace(`{${k}}`, String(v));
          });
        }
        return result;
      };
    },
    useLocale: () => "en",
    NextIntlClientProvider: ({ children }: any) => children,
  };
});
```

This way, existing `getByText("School Details")` assertions still pass.

**Step 4: Run full test suite**

Run: `cd frontend && npm test`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add frontend/__tests__/ frontend/jest.setup.* frontend/jest.config.*
git commit -m "test: update test setup with next-intl mocks for i18n"
```

---

## Task 12: Add new i18n-specific tests

**Files:**
- Create: `frontend/__tests__/i18n/middleware.test.ts`
- Create: `frontend/__tests__/i18n/translations.test.ts`

**Step 1: Write middleware test**

Create `frontend/__tests__/i18n/middleware.test.ts`:

```typescript
import { routing } from "@/i18n/routing";

describe("i18n routing config", () => {
  it("defines three locales", () => {
    expect(routing.locales).toEqual(["en", "ta", "ms"]);
  });

  it("uses en as default locale", () => {
    expect(routing.defaultLocale).toBe("en");
  });
});
```

**Step 2: Write translation completeness test**

Create `frontend/__tests__/i18n/translations.test.ts`:

```typescript
import en from "../../messages/en.json";
import ta from "../../messages/ta.json";
import ms from "../../messages/ms.json";

function getKeys(obj: any, prefix = ""): string[] {
  const keys: string[] = [];
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === "object" && obj[key] !== null) {
      keys.push(...getKeys(obj[key], fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

describe("Translation completeness", () => {
  const enKeys = getKeys(en);

  it("Tamil translations have all English keys", () => {
    const taKeys = getKeys(ta);
    const missing = enKeys.filter((k) => !taKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("Malay translations have all English keys", () => {
    const msKeys = getKeys(ms);
    const missing = enKeys.filter((k) => !msKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("no extra keys in Tamil that are not in English", () => {
    const taKeys = getKeys(ta);
    const extra = taKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });

  it("no extra keys in Malay that are not in English", () => {
    const msKeys = getKeys(ms);
    const extra = msKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });
});
```

**Step 3: Run new tests**

Run: `cd frontend && npx jest __tests__/i18n/ --no-cache`
Expected: All pass (since we added matching keys in all three files).

**Step 4: Commit**

```bash
git add frontend/__tests__/i18n/
git commit -m "test: add i18n routing and translation completeness tests"
```

---

## Task 13: Run full test suite + fix failures

**Step 1: Run all frontend tests**

Run: `cd frontend && npm test`

**Step 2: Fix any failures**

Common issues:
- Missing mock for `useTranslations` in older tests
- `Link` component import changes breaking snapshot tests
- Route path changes in test assertions

Fix each failure, re-run until green.

**Step 3: Run build**

Run: `cd frontend && npm run build`

This catches any SSR/ISR issues with the locale setup.

**Step 4: Commit**

```bash
git add frontend/
git commit -m "fix: resolve test failures from i18n migration"
```

---

## Task 14: Update CHANGELOG + sprint close

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `CLAUDE.md` (Next Sprint section)

**Step 1: Update CHANGELOG**

Add sprint 3.3 entry:

```markdown
## Sprint 3.3 — i18n Infrastructure (2026-03-03)

### Added
- Trilingual support (English, Tamil, Malay) using next-intl
- Locale-prefixed URLs: `/en/`, `/ta/`, `/ms/`
- Language switcher in Header (EN | தமிழ் | BM)
- ~162 strings extracted to `messages/en.json`, `messages/ta.json`, `messages/ms.json`
- Middleware for automatic locale detection and redirect
- Translation completeness tests (all three languages must have matching keys)
- LanguageSwitcher component

### Changed
- All pages moved under `app/[locale]/` directory
- All internal links use i18n-aware navigation
- Root `/` redirects to `/en/`
- Layout wraps children with NextIntlClientProvider
```

**Step 2: Update CLAUDE.md Next Sprint section**

Update to point to Sprint 3.4 (whatever is next on the roadmap).

**Step 3: Commit and push**

```bash
git add CHANGELOG.md CLAUDE.md
git commit -m "docs: Sprint 3.3 changelog and sprint close"
git push
```

---

## Summary

| Task | Description | Files touched | Estimated strings |
|------|-------------|--------------|-------------------|
| 1 | Install next-intl + routing config | 5 | 0 |
| 2 | Middleware + move pages under [locale] | 18 | 0 |
| 3 | Extract Header + Footer + common | 5 | ~25 |
| 4 | Language Switcher component | 2 | 3 |
| 5 | Extract School page + SchoolProfile | 5 | ~35 |
| 6 | Extract Map components | 6 | ~25 |
| 7 | Extract Constituency + DUN pages | 12 | ~40 |
| 8 | Extract Claim + Edit + Subscribe | 14 | ~55 |
| 9 | Extract Parliament Watch + News + History | 7 | ~15 |
| 10 | Update all Link imports | ~20 | 0 |
| 11 | Update existing tests | ~10 | 0 |
| 12 | Add i18n-specific tests | 2 | 0 |
| 13 | Full test suite + build | — | 0 |
| 14 | CHANGELOG + sprint close | 2 | 0 |

**Total**: ~162 strings × 3 languages, 14 tasks, ~27 components/pages modified.
