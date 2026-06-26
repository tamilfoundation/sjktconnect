/**
 * Sprint 28 — School URL slug helpers.
 *
 * Owner SEO investigation: apac.com.my outranks us at #3 for school-
 * name queries while we sit at #7. Their killer feature is school-name-
 * in-URL (`/pbd1088/SJK%20T%20SUBRAMANIYA%20BARATHEE,%20GELUGOR.html`)
 * — our URL is just `/school/PBD1088` which matches zero query words.
 *
 * Slug shape: `<name-slug>-<city-slug>-<moe-code-lowercase>`
 *   e.g. `subramaniya-barathee-gelugor-pbd1088`
 *        `ladang-bikam-segamat-jbd0050`
 *
 * Design notes:
 * - Name FIRST so the most-relevant SEO keywords are at the start of
 *   the URL path. Google weights early-path words more.
 * - moe_code at the END as the lookup primary key. Parse it back via
 *   the strict moe-code regex (3-4 letters + 3-4 digits) — every MOE
 *   code matches `^[A-Z]{3,4}\d{3,4}$`.
 * - City included for additional keyword density (matches apac.com.my
 *   pattern). Stable enough for our needs (city changes are rare).
 * - SJK(T) prefix stripped from name portion — keeps slug short and the
 *   prefix is implicit on a Tamil-schools-only site.
 * - All-lowercase, ASCII-only, hyphens between words. Standard URL
 *   slug practice.
 */

const SCHOOL_PATH_PREFIX = "/school";

// MOE code shape: 3-4 letters + 3-4 digits, e.g. PBD1088, ABDB006.
const MOE_CODE_RE = /^[a-z]{3,4}\d{3,4}$/i;

function slugifyPart(text: string): string {
  return text
    .toLowerCase()
    // Strip the SJK(T) / SJKT prefix entirely — implicit on this site.
    .replace(/^sjk\s*\(t\)\s*/i, "")
    .replace(/^sjkt\s+/i, "")
    // Replace anything that isn't [a-z0-9] with hyphens, collapse runs.
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export interface SchoolSlugInput {
  moe_code: string;
  short_name?: string | null;
  city?: string | null;
}

/**
 * Build the canonical slug-path for a school. Output ALWAYS contains
 * the moe_code at the end so the inverse `parseSchoolSlug` is exact.
 */
export function schoolPath(school: SchoolSlugInput): string {
  const namePart = slugifyPart(school.short_name ?? "");
  const cityPart = slugifyPart(school.city ?? "");
  const codePart = school.moe_code.toLowerCase();
  const parts = [namePart, cityPart, codePart].filter(Boolean);
  return `${SCHOOL_PATH_PREFIX}/${parts.join("-")}`;
}

/**
 * Extract the moe_code from a slug. Accepts both the new slug form
 * (`subramaniya-barathee-gelugor-pbd1088`) and the legacy bare-code
 * form (`PBD1088`) so the route handler can serve both transparently
 * while we redirect from the legacy shape to the canonical one.
 *
 * Returns the uppercase moe_code, or null if the slug doesn't end in
 * a valid moe-code shape.
 */
export function parseSchoolSlug(slug: string): string | null {
  if (!slug) return null;
  // Legacy bare-code: /school/PBD1088
  if (MOE_CODE_RE.test(slug)) return slug.toUpperCase();
  // New slug: last hyphen-separated segment is the moe_code.
  const idx = slug.lastIndexOf("-");
  if (idx === -1) return null;
  const candidate = slug.slice(idx + 1);
  if (!MOE_CODE_RE.test(candidate)) return null;
  return candidate.toUpperCase();
}

/**
 * True when `slug` already matches the canonical slug for `school`.
 * Used by the route handler to decide whether to 301-redirect a stale
 * or bare-code visit to the current canonical URL.
 */
export function isCanonicalSchoolSlug(
  slug: string,
  school: SchoolSlugInput,
): boolean {
  const expected = schoolPath(school).slice(SCHOOL_PATH_PREFIX.length + 1);
  return slug === expected;
}
