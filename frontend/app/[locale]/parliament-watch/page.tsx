import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBriefs } from "@/lib/api";
import BriefsList from "@/components/BriefsList";

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
  const briefs = await fetchBriefs();

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        {t("heading")}
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        {t("intro")}
      </p>

      {/* What Parliament Watch Does */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("whatWeTrack")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800 mb-1">{t("trackMentions")}</p>
            <p className="text-sm text-gray-600">{t("trackMentionsDesc")}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800 mb-1">{t("trackScorecards")}</p>
            <p className="text-sm text-gray-600">{t("trackScorecardsDesc")}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-800 mb-1">{t("trackAlerts")}</p>
            <p className="text-sm text-gray-600">{t("trackAlertsDesc")}</p>
          </div>
        </div>
      </div>

      {/* Sitting Briefs */}
      {briefs.length > 0 && <BriefsList briefs={briefs} />}

      {/* Status + CTA */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-2">
          {t("monitoringOngoing")}
        </h2>
        <p className="text-blue-800 mb-4">
          {t("monitoringBody")}
        </p>
        <Link
          href="/subscribe"
          className="inline-block bg-primary-600 text-white font-medium px-5 py-2.5 rounded-lg hover:bg-primary-700 transition-colors"
        >
          {t("subscribeCta")}
        </Link>
      </div>

      {/* Explore existing data */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("exploreNow")}
        </h2>
        <p className="text-gray-600 mb-4">
          {t("exploreBody")}
        </p>
        <div className="flex flex-wrap gap-3">
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
