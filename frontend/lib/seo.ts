/**
 * SEO helpers for hreflang alternate links and canonical URLs.
 *
 * Each locale page is its own canonical so Google indexes /en/, /ta/,
 * and /ms/ independently. The hreflang `languages` map tells Google
 * how the three locale variants relate; `x-default` resolves the bare
 * `/path` URL to /en/.
 */

const BASE_URL = "https://tamilschool.org";
const LOCALES = ["en", "ta", "ms"] as const;
const DEFAULT_LOCALE = "en";

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
