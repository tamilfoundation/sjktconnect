import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBriefs, fetchAllMentions, fetchMeetingReports } from "@/lib/api";

export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("parliamentWatch");
  return {
    title: t("title"),
    description: t("intro"),
  };
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
  return `${s.toLocaleDateString("en-GB", opts)} – ${e.toLocaleDateString("en-GB", opts)}`;
}

export default async function ParliamentWatchPage() {
  const t = await getTranslations("parliamentWatch");
  const [meetingReports, briefs, mentions] = await Promise.all([
    fetchMeetingReports(),
    fetchBriefs(),
    fetchAllMentions(),
  ]);

  // Latest 3 briefs for the compact sitting summaries section
  const recentBriefs = briefs.slice(0, 3);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {t("heading")}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl">
          {t("intro")}
        </p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10">
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">{briefs.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("sittingsTracked")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">{mentions.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("totalMentionsCount")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">
            {new Set(mentions.map(m => m.mp_name).filter(Boolean)).size}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{t("mpsTracked")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">
            {new Set(mentions.flatMap(m => "schools" in m ? m.schools.map((s: { moe_code: string }) => s.moe_code) : [])).size}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{t("schoolsMentioned")}</p>
        </div>
      </div>

      {/* Intelligence Reports — 2-column grid */}
      {meetingReports.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xl font-bold text-gray-900 mb-1">
            {t("intelligenceReports")}
          </h2>
          <p className="text-sm text-gray-500 mb-5">
            {t("intelligenceReportsDesc")}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {meetingReports.map((report) => (
              <Link
                key={report.id}
                href={`/parliament-watch/${report.id}`}
                className="block bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-5"
              >
                <p className="text-xs font-medium text-primary-600 uppercase tracking-wide mb-1">
                  {formatDateRange(report.start_date, report.end_date)}
                </p>
                <h3 className="text-base font-semibold text-gray-900 mb-2">
                  {report.short_name}
                </h3>
                <div className="flex gap-2 mb-3">
                  <span className="inline-flex items-center text-xs font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                    {report.sitting_count} sittings
                  </span>
                  <span className="inline-flex items-center text-xs font-medium bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full">
                    {report.total_mentions} mentions
                  </span>
                </div>
                {report.executive_summary && (
                  <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">
                    {report.executive_summary.replace(/<[^>]*>/g, "")}
                  </p>
                )}
                <span className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 mt-3">
                  {t("readReport")}
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Latest Sitting Summaries — compact list */}
      {recentBriefs.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            {t("latestSittings")}
          </h2>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {recentBriefs.map((brief) => (
              <div key={brief.id} className="flex items-center justify-between px-5 py-3.5">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-400 mb-0.5">
                    {new Date(brief.sitting_date).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {brief.title.replace(/\s*[—–-]\s*\d{1,2}\s+\w+\s+\d{4}$/, "")}
                  </p>
                </div>
                <span className="ml-3 shrink-0 inline-flex items-center text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full">
                  {brief.mention_count} {brief.mention_count === 1 ? "mention" : "mentions"}
                </span>
              </div>
            ))}
          </div>
          {briefs.length > 3 && (
            <p className="text-center mt-3">
              <Link
                href="/parliament-watch/sittings"
                className="text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                {t("viewAllSittings", { count: briefs.length })} →
              </Link>
            </p>
          )}
        </section>
      )}

      {/* CTA Banner */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-100 p-6 mb-8 text-center">
        <h2 className="text-lg font-semibold text-primary-900 mb-2">
          {t("stayInformed")}
        </h2>
        <p className="text-sm text-primary-800 mb-4 max-w-xl mx-auto">
          {t("stayInformedBody")}
        </p>
        <Link
          href="/subscribe"
          className="inline-block bg-primary-600 text-white font-medium px-5 py-2.5 rounded-lg hover:bg-primary-700 transition-colors text-sm"
        >
          {t("subscribeCta")}
        </Link>
      </div>
    </div>
  );
}
