import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchBriefs } from "@/lib/api";
import BriefsList from "@/components/BriefsList";

export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("parliamentWatch");
  return {
    title: `${t("sittingBriefs")} — ${t("heading")}`,
    description: t("sittingBriefsDesc"),
  };
}

export default async function SittingsPage() {
  const t = await getTranslations("parliamentWatch");
  const briefs = await fetchBriefs();

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href="/parliament-watch" className="hover:text-primary-600 transition-colors">
          {t("backToParliamentWatch")}
        </Link>
        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-900 font-medium">{t("sittingBriefs")}</span>
      </nav>

      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {t("sittingBriefs")}
      </h1>
      <p className="text-lg text-gray-600 max-w-2xl mb-8">
        {t("sittingBriefsDesc")}
      </p>

      <BriefsList briefs={briefs} />
    </div>
  );
}
