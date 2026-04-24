import type { MetadataRoute } from "next";

const BASE_URL = "https://tamilschool.org";
const LOCALES = ["en", "ta", "ms"];

/**
 * Dynamic XML sitemap with hreflang alternates for all public pages.
 *
 * Each path generates one <url> entry per locale (en, ta, ms), each with
 * xhtml:link alternates pointing to all three versions.
 *
 * Covers:
 * - Static pages (about, news, constituencies, etc.)
 * - Dynamic school pages (528 schools)
 * - Dynamic constituency pages
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

  const staticEntries = staticPaths.flatMap((path) =>
    buildLocaleEntries(path, path === "/news" ? "daily" : "weekly", path === "/" ? 1.0 : 0.7)
  );

  // Dynamic school pages
  let schoolEntries: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${apiBase}/api/v1/schools/map/`);
    if (res.ok) {
      const schools: { moe_code: string }[] = await res.json();
      schoolEntries = schools.flatMap((s) =>
        buildLocaleEntries(`/school/${s.moe_code}`, "monthly", 0.8)
      );
    }
  } catch {
    // API unavailable during build — skip dynamic entries
  }

  // Dynamic constituency pages (paginated — ~222 constituencies across multiple pages)
  let constituencyEntries: MetadataRoute.Sitemap = [];
  try {
    const allConstituencies: { code: string }[] = [];
    let url: string | null = `${apiBase}/api/v1/constituencies/`;
    while (url) {
      const res: Response = await fetch(url);
      if (!res.ok) break;
      const data: { results?: { code: string }[]; next?: string | null; code?: string }[] | {
        results?: { code: string }[];
        next?: string | null;
      } = await res.json();
      const results: { code: string }[] =
        (data as { results?: { code: string }[] }).results || (data as { code: string }[]);
      allConstituencies.push(...results);
      url = (data as { next?: string | null }).next || null;
    }
    constituencyEntries = allConstituencies.flatMap((c) =>
      buildLocaleEntries(`/constituency/${c.code}`, "monthly", 0.7)
    );
  } catch {
    // API unavailable during build
  }

  return [...staticEntries, ...schoolEntries, ...constituencyEntries];
}

/** Build one <url> entry per locale for a given path, with cross-locale alternates. */
function buildLocaleEntries(
  path: string,
  changeFrequency: "daily" | "weekly" | "monthly",
  priority: number,
): MetadataRoute.Sitemap {
  const suffix = path === "/" ? "" : path;
  return LOCALES.map((locale) => ({
    url: `${BASE_URL}/${locale}${suffix}`,
    lastModified: new Date(),
    changeFrequency,
    priority,
    alternates: {
      languages: Object.fromEntries(
        LOCALES.map((l) => [l, `${BASE_URL}/${l}${suffix}`])
      ),
    },
  }));
}
