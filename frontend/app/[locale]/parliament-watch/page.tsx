import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBriefs, fetchAllMentions, fetchMeetingReports } from "@/lib/api";
import MeetingReportsGrid from "@/components/MeetingReportsGrid";

export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("parliamentWatch");
  return {
    title: t("title"),
    description: t("intro"),
  };
}

export default async function ParliamentWatchPage() {
  const t = await getTranslations("parliamentWatch");
  const [meetingReports, briefs, mentions] = await Promise.all([
    fetchMeetingReports(),
    fetchBriefs(),
    fetchAllMentions(),
  ]);

  // Latest 4 briefs for the compact sitting summaries section
  const recentBriefs = briefs.slice(0, 4);

  // Meaningful stats
  const meetingsWithReports = meetingReports.filter(r => r.total_mentions > 0).length;
  const uniqueMPs = new Set(mentions.map(m => m.mp_name).filter(Boolean)).size;
  // Calculate years of coverage from meeting date range
  const meetingDates = meetingReports.map(r => r.start_date).filter(Boolean).sort();
  const yearsTracked = meetingDates.length >= 2
    ? Math.max(1, Math.ceil(
        (new Date(meetingDates[meetingDates.length - 1]).getTime() - new Date(meetingDates[0]).getTime())
        / (365.25 * 24 * 60 * 60 * 1000)
      ))
    : 1;

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
          <p className="text-2xl font-bold text-primary-600">{meetingReports.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("meetingsCovered")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">{meetingsWithReports}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("intelligenceReports")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">{uniqueMPs}</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("mpsTracked")}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-primary-600">{yearsTracked}+</p>
          <p className="text-xs text-gray-500 mt-0.5">{t("yearsOfData")}</p>
        </div>
      </div>

      {/* Meeting Reports — 2-column grid with pagination */}
      {meetingReports.length > 0 && (
        <MeetingReportsGrid reports={meetingReports} />
      )}

      {/* Latest Sitting Summaries — card grid matching meeting reports style */}
      {recentBriefs.length > 0 && (
        <section className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-1">
            {t("latestSittings")}
          </h2>
          <p className="text-sm text-gray-500 mb-5">{t("sittingBriefsDesc")}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {recentBriefs.map((brief) => {
              const headline = brief.title.replace(/\s*[—–-]\s*\d{1,2}\s+\w+\s+\d{4}$/, "");
              const blurb = brief.summary_html
                .replace(/<[^>]*>/g, " ")
                .replace(/\s+/g, " ")
                .trim()
                .slice(0, 150)
                .replace(/\s+\S*$/, "") + "...";

              return (
                <Link
                  key={brief.id}
                  href={`/parliament-watch/sittings/${brief.id}`}
                  className="group block bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all p-5"
                >
                  <p className="text-xs text-gray-400 mb-1.5">
                    {new Date(brief.sitting_date).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                  <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary-700 transition-colors mb-2 line-clamp-2">
                    {headline}
                  </h3>
                  <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                    {blurb}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">
                      {brief.mention_count}{" "}
                      {brief.mention_count === 1 ? "mention" : "mentions"}
                    </span>
                    <span className="text-sm font-medium text-primary-600 group-hover:text-primary-700">
                      {t("readFullReport")} &rarr;
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>

          {briefs.length > 4 && (
            <p className="text-center mt-4">
              <Link
                href="/parliament-watch/sittings"
                className="text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                {t("viewAllSittings", { count: briefs.length })} &rarr;
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
