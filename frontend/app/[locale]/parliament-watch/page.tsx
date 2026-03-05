import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBriefs, fetchAllMentions, fetchMeetingReports } from "@/lib/api";
import BriefsList from "@/components/BriefsList";
import MeetingReportsList from "@/components/MeetingReportsList";
import MentionsList from "@/components/MentionsList";

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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
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
            {new Set(mentions.flatMap(m => "schools" in m ? m.schools.map(s => s.moe_code) : [])).size}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{t("schoolsMentioned")}</p>
        </div>
      </div>

      {/* Section 1: Meeting Reports */}
      {meetingReports.length > 0 && <MeetingReportsList reports={meetingReports} />}

      {/* Section 2: Sitting Reports */}
      {briefs.length > 0 && <BriefsList briefs={briefs} />}

      {/* Section 3: Individual Mentions */}
      <div className="mb-8">
        <MentionsList mentions={mentions} showSchools />
      </div>

      {/* CTA */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-100 p-6 mb-8">
        <h2 className="text-lg font-semibold text-primary-900 mb-2">
          {t("monitoringOngoing")}
        </h2>
        <p className="text-sm text-primary-800 mb-4 max-w-xl">
          {t("monitoringBody")}
        </p>
        <Link
          href="/subscribe"
          className="inline-block bg-primary-600 text-white font-medium px-5 py-2.5 rounded-lg hover:bg-primary-700 transition-colors text-sm"
        >
          {t("subscribeCta")}
        </Link>
      </div>

      {/* Explore */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("exploreNow")}
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          {t("exploreBody")}
        </p>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/constituencies"
            className="text-primary-600 hover:text-primary-700 font-medium text-sm"
          >
            {t("constituencyPages")} →
          </Link>
          <Link
            href="/"
            className="text-primary-600 hover:text-primary-700 font-medium text-sm"
          >
            {t("schoolMap")} →
          </Link>
        </div>
      </div>
    </div>
  );
}
