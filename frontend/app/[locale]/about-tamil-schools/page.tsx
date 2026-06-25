import { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buildAlternates } from "@/lib/seo";
import { fetchNationalStats, fetchAllSchools } from "@/lib/api";

export const revalidate = 86400;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations("aboutTamilSchools");
  return {
    title: t("title"),
    description: t("intro"),
    openGraph: {
      title: t("title"),
      description: t("intro"),
      type: "article",
      siteName: "SJK(T) Connect",
    },
    alternates: buildAlternates("/about-tamil-schools", locale as "en" | "ta" | "ms"),
  };
}

interface StateRow {
  state: string;
  schools: number;
  students: number;
}

function aggregateByState(schools: { state: string; enrolment: number }[]): StateRow[] {
  const map = new Map<string, StateRow>();
  for (const s of schools) {
    const row = map.get(s.state) || { state: s.state, schools: 0, students: 0 };
    row.schools += 1;
    row.students += s.enrolment ?? 0;
    map.set(s.state, row);
  }
  return Array.from(map.values()).sort((a, b) => b.schools - a.schools);
}

export default async function AboutTamilSchoolsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("aboutTamilSchools");

  // Pull live stats. If the API is unavailable during build/ISR, fall back
  // to last-known values so the page still ranks for "how many tamil schools".
  let stats;
  let stateRows: StateRow[] = [];
  try {
    stats = await fetchNationalStats();
    const schools = await fetchAllSchools();
    stateRows = aggregateByState(schools);
  } catch {
    stats = {
      total_schools: 528,
      total_students: 69900,
      total_teachers: 8731,
      total_preschool: 7541,
      total_special_needs: 575,
      states: 11,
      constituencies_with_schools: 122,
      schools_under_30_students: 154,
    };
  }

  const fmt = (n: number) =>
    n.toLocaleString(
      locale === "ta" ? "ta-IN" : locale === "ms" ? "ms-MY" : "en-MY",
    );

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
        {t("heading")}
      </h1>
      <p className="text-lg text-gray-600 mb-12">
        {t("intro", {
          totalSchools: fmt(stats.total_schools),
          // Lead with the TOTAL children attending SJK(T) facilities
          // (primary + preschool + special education), matching the
          // breakdown that follows in the body. Was previously a
          // hardcoded "69,000" string that drifted from live data.
          totalChildren: fmt(
            stats.total_students +
              stats.total_preschool +
              stats.total_special_needs,
          ),
          states: fmt(stats.states),
        })}
      </p>

      {/* Q1: How many */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">
          {t("howManyHeading")}
        </h2>
        <p className="text-gray-700 leading-relaxed">
          {t("howManyBody", {
            totalSchools: fmt(stats.total_schools),
            totalStudents: fmt(stats.total_students),
            totalTeachers: fmt(stats.total_teachers),
            states: fmt(stats.states),
            totalPreschool: fmt(stats.total_preschool),
            totalSpecialNeeds: fmt(stats.total_special_needs),
            schoolsUnder30: fmt(stats.schools_under_30_students),
          })}
        </p>
      </section>

      {/* Q2: By state */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">
          {t("byStateHeading")}
        </h2>
        <p className="text-gray-700 mb-4">{t("byStateIntro")}</p>
        {stateRows.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-left">
                <tr>
                  <th className="px-4 py-2 font-semibold">
                    {t("byStateColState")}
                  </th>
                  <th className="px-4 py-2 font-semibold text-right">
                    {t("byStateColSchools")}
                  </th>
                  <th className="px-4 py-2 font-semibold text-right">
                    {t("byStateColStudents")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {stateRows.map((r) => (
                  <tr key={r.state} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-900">
                      <Link
                        href={`/?state=${encodeURIComponent(r.state)}`}
                        className="text-primary-600 hover:text-primary-800 hover:underline"
                      >
                        {r.state}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-700 font-medium tabular-nums">
                      {fmt(r.schools)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-700 tabular-nums">
                      {fmt(r.students)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Q3: What is */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">
          {t("whatIsHeading")}
        </h2>
        <p className="text-gray-700 leading-relaxed">{t("whatIsBody")}</p>
      </section>

      {/* CTA */}
      <section className="bg-primary-50 border border-primary-100 rounded-lg p-6">
        <h2 className="text-xl font-bold text-primary-900 mb-2">
          {t("ctaHeading")}
        </h2>
        <p className="text-primary-800 mb-4">{t("ctaBody")}</p>
        <Link
          href="/"
          className="inline-flex items-center text-primary-700 hover:text-primary-900 font-semibold"
        >
          {t("ctaButton")}
        </Link>
      </section>
    </div>
  );
}
