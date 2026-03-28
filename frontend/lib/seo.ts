/**
 * SEO helpers for hreflang alternate links and canonical URLs.
 *
 * Fixes Google Search Console "Duplicate without user-selected canonical"
 * by telling Google which locale variant is canonical and how they relate.
 */

const BASE_URL = "https://tamilschool.org";
const LOCALES = ["en", "ta", "ms"] as const;
const DEFAULT_LOCALE = "en";

/**
 * Build the `alternates` object for Next.js Metadata.
 *
 * @param path - The path after the locale segment, e.g. "/about" or "/school/ABC1234".
 *               Pass "/" or "" for the homepage.
 */
export function buildAlternates(path: string) {
  const cleanPath = path === "/" ? "" : path;

  return {
    canonical: `${BASE_URL}/${DEFAULT_LOCALE}${cleanPath}`,
    languages: Object.fromEntries(
      LOCALES.map((locale) => [locale, `${BASE_URL}/${locale}${cleanPath}`])
    ) as Record<string, string>,
  };
}
