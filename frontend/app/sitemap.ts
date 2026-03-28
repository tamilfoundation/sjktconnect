import type { MetadataRoute } from "next";

const BASE_URL = "https://tamilschool.org";
const LOCALES = ["en", "ta", "ms"];

/**
 * Dynamic XML sitemap with hreflang alternates for all public pages.
 *
 * Covers:
 * - Static pages (about, news, constituencies, etc.)
 * - Dynamic school pages (528 schools)
 * - Dynamic constituency pages
 *
 * Google will use this + the <link rel="alternate"> tags in HTML
 * to resolve the "Duplicate without user-selected canonical" issue.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Static pages
  const staticPaths = [
    "/",
    "/about",
    "/about-tamil-schools",
    "/news",
    "/constituencies",
    "/parliament-watch",
    "/parliament-watch/sittings",
    "/data",
    "/faq",
    "/issues",
    "/donate",
    "/contact",
    "/subscribe",
    "/resources/lps-toolkit",
    "/resources/pta-toolkit",
    "/privacy",
    "/terms",
    "/cookies",
  ];

  const staticEntries: MetadataRoute.Sitemap = staticPaths.map((path) => ({
    url: `${BASE_URL}/en${path === "/" ? "" : path}`,
    lastModified: new Date(),
    changeFrequency: path === "/news" ? "daily" : "weekly",
    priority: path === "/" ? 1.0 : 0.7,
    alternates: {
      languages: Object.fromEntries(
        LOCALES.map((locale) => [
          locale,
          `${BASE_URL}/${locale}${path === "/" ? "" : path}`,
        ])
      ),
    },
  }));

  // Dynamic school pages
  let schoolEntries: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${apiBase}/api/v1/schools/map/`);
    if (res.ok) {
      const schools: { moe_code: string }[] = await res.json();
      schoolEntries = schools.map((s) => ({
        url: `${BASE_URL}/en/school/${s.moe_code}`,
        lastModified: new Date(),
        changeFrequency: "monthly" as const,
        priority: 0.8,
        alternates: {
          languages: Object.fromEntries(
            LOCALES.map((locale) => [
              locale,
              `${BASE_URL}/${locale}/school/${s.moe_code}`,
            ])
          ),
        },
      }));
    }
  } catch {
    // API unavailable during build — skip dynamic entries
  }

  // Dynamic constituency pages
  let constituencyEntries: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${apiBase}/api/v1/constituencies/`);
    if (res.ok) {
      const data = await res.json();
      const constituencies: { code: string }[] = data.results || data;
      constituencyEntries = constituencies.map((c) => ({
        url: `${BASE_URL}/en/constituency/${c.code}`,
        lastModified: new Date(),
        changeFrequency: "monthly" as const,
        priority: 0.7,
        alternates: {
          languages: Object.fromEntries(
            LOCALES.map((locale) => [
              locale,
              `${BASE_URL}/${locale}/constituency/${c.code}`,
            ])
          ),
        },
      }));
    }
  } catch {
    // API unavailable during build
  }

  return [...staticEntries, ...schoolEntries, ...constituencyEntries];
}
