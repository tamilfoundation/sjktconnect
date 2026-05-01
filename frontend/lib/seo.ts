/**
 * SEO helpers — hreflang alternates, canonical URLs, and metadata builders
 * for school / constituency / DUN detail pages.
 *
 * Each locale page is its own canonical so Google indexes /en/, /ta/,
 * and /ms/ independently. The hreflang `languages` map relates the three
 * locale variants; `x-default` resolves the bare `/path` URL to /en/.
 *
 * (Sprint 22) Metadata builders produce locale-aware titles + data-rich
 * descriptions. GSC shows that small-school English pages were getting
 * generic prose snippets ("X is a Tamil primary school...") while Malay
 * pages got rich structured snippets ("Alamat: ... E-mel: ..."). The
 * fix: meta description for every locale carries labelled key/value
 * data (Address/Alamat/முகவரி + E-mel + Telefon + Lokasi + Bantuan)
 * so Google's snippet picker has consistent structured signal.
 */

import type { Metadata } from "next";
import type { SchoolDetail, ConstituencyDetail, DUNDetail } from "@/lib/types";

const BASE_URL = "https://tamilschool.org";
const LOCALES = ["en", "ta", "ms"] as const;
const DEFAULT_LOCALE = "en";

/** Fallback hero image — branded SVG shipped at /public/school-placeholder.svg.
 *  Used when a school has no SchoolImage records. Ensures every school page
 *  emits a real <img> tag + og:image for Google's SERP thumbnail picker. */
export const SCHOOL_PLACEHOLDER_URL = `${BASE_URL}/school-placeholder.svg`;

type Locale = (typeof LOCALES)[number];

/**
 * Build the `alternates` object for Next.js Metadata.
 *
 * @param path - The path after the locale segment, e.g. "/about" or
 *               "/school/ABC1234". Pass "/" or "" for the homepage.
 * @param currentLocale - The locale of the page being rendered. The
 *               canonical URL is set to the same locale so Google
 *               indexes each translated page independently. Pre-Sprint-22
 *               canonical was hard-coded to /en/, which silently de-duped
 *               every /ta/ and /ms/ page out of the index (~2.36k pages).
 */
export function buildAlternates(
  path: string,
  currentLocale: Locale = DEFAULT_LOCALE,
) {
  const cleanPath = path === "/" ? "" : path;

  return {
    canonical: `${BASE_URL}/${currentLocale}${cleanPath}`,
    languages: {
      ...Object.fromEntries(
        LOCALES.map((locale) => [locale, `${BASE_URL}/${locale}${cleanPath}`]),
      ),
      "x-default": `${BASE_URL}/${DEFAULT_LOCALE}${cleanPath}`,
    } as Record<string, string>,
  };
}

// ─── Locale-aware label maps ─────────────────────────────────────────────
//
// Mirrors `messages/{locale}.json`'s `schoolProfile` namespace — duplicated
// here because metadata generation runs before next-intl messages are
// loaded, and calling getTranslations() inside generateMetadata adds an
// async dependency for what is otherwise pure string assembly.

interface SchoolLabels {
  schoolType: string;       // "Tamil primary school" / "Sekolah jenis ..." / "தமிழ் வகைப் பள்ளி"
  in: string;               // "in" / "di" / "—"
  address: string;
  email: string;
  phone: string;
  location: string;
  assistance: string;
  students: string;
  teachers: string;
  grade: string;
  locationBandar: string;
  locationLuarBandar: string;
  assistanceSBK: string;
  assistanceSK: string;
  assistanceSABK: string;
}

const SCHOOL_LABELS: Record<Locale, SchoolLabels> = {
  en: {
    schoolType: "Tamil primary school",
    in: "in",
    address: "Address",
    email: "Email",
    phone: "Phone",
    location: "Location",
    assistance: "Assistance",
    students: "students",
    teachers: "teachers",
    grade: "Grade",
    locationBandar: "Urban",
    locationLuarBandar: "Rural",
    assistanceSBK: "Government-Aided",
    assistanceSK: "Government",
    assistanceSABK: "Government-Aided Religious",
  },
  ms: {
    schoolType: "Sekolah jenis kebangsaan (Tamil)",
    in: "di",
    address: "Alamat",
    email: "E-mel",
    phone: "Telefon",
    location: "Jenis Lokasi",
    assistance: "Jenis Bantuan",
    students: "murid",
    teachers: "guru",
    grade: "Gred",
    locationBandar: "Bandar",
    locationLuarBandar: "Luar Bandar",
    assistanceSBK: "Bantuan Kerajaan",
    assistanceSK: "Sekolah Kerajaan",
    assistanceSABK: "Bantuan Kerajaan Agama",
  },
  ta: {
    schoolType: "தமிழ் ஆரம்பப் பள்ளி",
    in: "—",
    address: "முகவரி",
    email: "மின்னஞ்சல்",
    phone: "தொலைபேசி",
    location: "இடம்",
    assistance: "உதவி",
    students: "மாணவர்கள்",
    teachers: "ஆசிரியர்கள்",
    grade: "கிரேடு",
    locationBandar: "நகர்ப்புறம்",
    locationLuarBandar: "ஊரகம்",
    assistanceSBK: "அரசு உதவி",
    assistanceSK: "அரசுப் பள்ளி",
    assistanceSABK: "அரசு உதவி சமயப் பள்ளி",
  },
};

interface AreaLabels {
  parliamentaryConstituency: string;
  stateConstituency: string;
  mp: string;
  adun: string;
  schools: string;
  schoolsSingular: string;
  in: string;
  represents: string;
}

const AREA_LABELS: Record<Locale, AreaLabels> = {
  en: {
    parliamentaryConstituency: "Parliamentary Constituency",
    stateConstituency: "ADUN (State Constituency)",
    mp: "MP",
    adun: "ADUN",
    schools: "Tamil schools",
    schoolsSingular: "Tamil school",
    in: "in",
    represents: "represents",
  },
  ms: {
    parliamentaryConstituency: "Kawasan Parlimen",
    stateConstituency: "DUN (Dewan Undangan Negeri)",
    mp: "Ahli Parlimen",
    adun: "ADUN",
    schools: "sekolah Tamil",
    schoolsSingular: "sekolah Tamil",
    in: "di",
    represents: "mewakili",
  },
  ta: {
    parliamentaryConstituency: "நாடாளுமன்றத் தொகுதி",
    stateConstituency: "மாநிலத் தொகுதி (DUN)",
    mp: "நாடாளுமன்ற உறுப்பினர்",
    adun: "மாநில உறுப்பினர்",
    schools: "தமிழ்ப் பள்ளிகள்",
    schoolsSingular: "தமிழ்ப் பள்ளி",
    in: "—",
    represents: "பிரதிநிதித்துவம் செய்கிறார்",
  },
};

function normaliseLocale(input: string): Locale {
  return (LOCALES as readonly string[]).includes(input)
    ? (input as Locale)
    : DEFAULT_LOCALE;
}

function translateLocationType(raw: string | null | undefined, l: SchoolLabels): string {
  if (!raw) return "";
  if (raw === "Bandar") return l.locationBandar;
  if (raw === "Luar Bandar") return l.locationLuarBandar;
  return raw;
}

function translateAssistanceType(raw: string | null | undefined, l: SchoolLabels): string {
  if (!raw) return "";
  if (raw === "SBK") return l.assistanceSBK;
  if (raw === "SK") return l.assistanceSK;
  if (raw === "SABK") return l.assistanceSABK;
  return raw;
}

/** True when `town` is meaningfully different from the school's display name. */
function townDistinctFromName(town: string | null | undefined, displayName: string): boolean {
  if (!town) return false;
  const t = town.trim().toLowerCase();
  const n = displayName.trim().toLowerCase();
  return t.length > 0 && !n.includes(t) && !t.includes(n);
}

/**
 * Build Metadata for a school detail page.
 *
 * Title: "SJK(T) Trolak | 17 Students, Grade C | Pekan Trolak, Perak"
 *   — town inserted before state when town ≠ school name (helps catch
 *     "tamil school pekan trolak"-style queries that GSC shows are coming
 *     in but with no good landing page).
 *
 * Description (Sprint 22): labelled key/value list so Google's snippet
 *   picker has structured data on every locale.
 *   English:  "Tamil primary school in Pekan Trolak, Perak. Address: ... · Email: ... · Phone: ... · Location: Rural · Assistance: Government. 17 students, 9 teachers."
 *   Malay:    "Sekolah jenis kebangsaan (Tamil) di Pekan Trolak, Perak. Alamat: ... · E-mel: ... · Telefon: ... · Jenis Lokasi: ... · Jenis Bantuan: ..."
 *   Tamil:    Same shape, Tamil script.
 */
export function buildSchoolMetadata(
  school: SchoolDetail,
  localeRaw: string,
): Metadata {
  const locale = normaliseLocale(localeRaw);
  const l = SCHOOL_LABELS[locale];

  const displayName = school.short_name || school.name;
  const town = school.city || school.ppd || "";

  // Title
  const stats: string[] = [];
  if (school.enrolment) {
    const studentsCapitalised =
      locale === "en" ? "Students" : l.students.charAt(0).toUpperCase() + l.students.slice(1);
    stats.push(`${school.enrolment.toLocaleString()} ${studentsCapitalised}`);
  }
  if (school.grade) stats.push(`${l.grade} ${school.grade}`);
  const locationTail = townDistinctFromName(town, displayName)
    ? `${town}, ${school.state}`
    : school.state;
  const title = stats.length
    ? `${displayName} | ${stats.join(", ")} | ${locationTail}`
    : `${displayName} | ${locationTail} — SJK(T) Connect`;

  // Description — labelled key/value pairs separated by " · "
  const fullAddress = [school.address, `${school.postcode} ${school.city}`.trim(), school.state]
    .filter((part) => part && part.trim().length > 0)
    .join(", ");
  const dataPairs: string[] = [];
  if (fullAddress) dataPairs.push(`${l.address}: ${fullAddress}`);
  if (school.email) dataPairs.push(`${l.email}: ${school.email}`);
  if (school.phone) dataPairs.push(`${l.phone}: ${school.phone}`);
  const locationT = translateLocationType(school.location_type, l);
  if (locationT) dataPairs.push(`${l.location}: ${locationT}`);
  const assistanceT = translateAssistanceType(school.assistance_type, l);
  if (assistanceT) dataPairs.push(`${l.assistance}: ${assistanceT}`);

  const intro =
    locale === "ta"
      ? `${displayName} — ${l.schoolType}, ${town || school.state}.`
      : `${l.schoolType} ${l.in} ${town || school.state}, ${school.state === town ? "" : school.state}.`.replace(/, \./, ".");
  const stats2: string[] = [];
  if (school.enrolment) stats2.push(`${school.enrolment.toLocaleString()} ${l.students}`);
  if (school.teacher_count) stats2.push(`${school.teacher_count.toLocaleString()} ${l.teachers}`);
  const description = [intro, dataPairs.join(" · "), stats2.join(", ")]
    .filter((s) => s && s.trim().length > 0)
    .join(" ");

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      siteName: "SJK(T) Connect",
      images: [{ url: school.image_url || SCHOOL_PLACEHOLDER_URL }],
    },
    alternates: buildAlternates(`/school/${school.moe_code}`, locale),
  };
}

/**
 * Build Metadata for a parliamentary constituency detail page.
 *
 * Title: "Indera Mahkota — MP, Tamil Schools | P140, Pahang"
 * Description: MP name + Tamil school count + scorecard tease.
 */
export function buildConstituencyMetadata(
  c: ConstituencyDetail,
  localeRaw: string,
): Metadata {
  const locale = normaliseLocale(localeRaw);
  const a = AREA_LABELS[locale];
  const schoolCount = c.schools.length;
  const schoolsWord = schoolCount === 1 ? a.schoolsSingular : a.schools;

  const titleHead =
    locale === "en"
      ? `${c.name} — ${a.mp}, ${a.schools}`
      : locale === "ms"
        ? `${c.name} — ${a.mp}, ${a.schools}`
        : `${c.name} — ${a.mp}, ${a.schools}`;
  const title = `${titleHead} | ${c.code}, ${c.state}`;

  const description =
    locale === "en"
      ? `${c.mp_name} (${c.mp_party}) ${a.represents} ${c.name} (${c.code}) ${a.in} ${c.state}. ${schoolCount} ${schoolsWord}.${c.scorecard?.total_mentions ? ` ${c.scorecard.total_mentions} parliamentary mentions tracked.` : ""} View MP scorecard, schools, news.`
      : locale === "ms"
        ? `${c.mp_name} (${c.mp_party}) ${a.represents} ${c.name} (${c.code}) ${a.in} ${c.state}. ${schoolCount} ${schoolsWord}.${c.scorecard?.total_mentions ? ` ${c.scorecard.total_mentions} sebutan parlimen direkodkan.` : ""} Lihat skorkad ${a.mp}, sekolah, berita.`
        : `${c.mp_name} (${c.mp_party}) — ${c.name} (${c.code}), ${c.state}. ${schoolCount} ${schoolsWord}.${c.scorecard?.total_mentions ? ` ${c.scorecard.total_mentions} நாடாளுமன்றக் குறிப்புகள்.` : ""}`;

  return {
    title,
    description,
    openGraph: { title, description, type: "website", siteName: "SJK(T) Connect" },
    alternates: buildAlternates(`/constituency/${c.code}`, locale),
  };
}

/**
 * Build Metadata for a state legislative assembly (DUN) detail page.
 *
 * Title: "Tualang Sekah ADUN — Tamil Schools, MP | N12, Perak"
 */
export function buildDUNMetadata(
  d: DUNDetail,
  localeRaw: string,
): Metadata {
  const locale = normaliseLocale(localeRaw);
  const a = AREA_LABELS[locale];
  const schoolCount = d.schools.length;
  const schoolsWord = schoolCount === 1 ? a.schoolsSingular : a.schools;

  const titleHead =
    locale === "en"
      ? `${d.name} ${a.adun} — ${a.schools}, ${a.mp}`
      : locale === "ms"
        ? `${a.adun} ${d.name} — ${a.schools}, ${a.mp}`
        : `${d.name} ${a.adun} — ${a.schools}, ${a.mp}`;
  const title = `${titleHead} | ${d.code}, ${d.state}`;

  const description =
    locale === "en"
      ? `${d.name} (${d.code}) is a state constituency in ${d.state} under ${d.constituency_name} (${d.constituency_code}). ${schoolCount} ${schoolsWord}.${d.adun_name ? ` ADUN: ${d.adun_name} (${d.adun_party}).` : ""}`
      : locale === "ms"
        ? `${d.name} (${d.code}) adalah DUN ${a.in} ${d.state}, di bawah parlimen ${d.constituency_name} (${d.constituency_code}). ${schoolCount} ${schoolsWord}.${d.adun_name ? ` ADUN: ${d.adun_name} (${d.adun_party}).` : ""}`
        : `${d.name} (${d.code}) — ${d.state}, ${d.constituency_name} (${d.constituency_code}). ${schoolCount} ${schoolsWord}.${d.adun_name ? ` ADUN: ${d.adun_name} (${d.adun_party}).` : ""}`;

  return {
    title,
    description,
    openGraph: { title, description, type: "website", siteName: "SJK(T) Connect" },
    alternates: buildAlternates(`/dun/${d.id}`, locale),
  };
}

/**
 * Render an EducationalOrganization JSON-LD payload for a school.
 * Returns a JSON.stringify-able object — the page wraps it in
 * `<script type="application/ld+json">`.
 */
export function buildSchoolJsonLd(school: SchoolDetail): Record<string, unknown> {
  const url = `${BASE_URL}/en/school/${school.moe_code}`;
  const obj: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    "@id": url,
    name: school.short_name || school.name,
    alternateName: school.name_tamil || undefined,
    url,
    address: {
      "@type": "PostalAddress",
      streetAddress: school.address || undefined,
      postalCode: school.postcode || undefined,
      addressLocality: school.city || undefined,
      addressRegion: school.state,
      addressCountry: "MY",
    },
    email: school.email || undefined,
    telephone: school.phone || undefined,
    geo:
      school.gps_lat && school.gps_lng
        ? {
            "@type": "GeoCoordinates",
            latitude: Number(school.gps_lat),
            longitude: Number(school.gps_lng),
          }
        : undefined,
    image: school.image_url || SCHOOL_PLACEHOLDER_URL,
    numberOfStudents: school.enrolment || undefined,
  };
  // Strip undefined values so the rendered JSON is clean.
  Object.keys(obj).forEach((k) => obj[k] === undefined && delete obj[k]);
  if (obj.address && typeof obj.address === "object") {
    const addr = obj.address as Record<string, unknown>;
    Object.keys(addr).forEach((k) => addr[k] === undefined && delete addr[k]);
  }
  return obj;
}
