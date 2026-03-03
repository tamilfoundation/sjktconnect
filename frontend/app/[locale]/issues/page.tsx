import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("issuesPage");
  return {
    title: t("title"),
    description: t("intro"),
  };
}

export default async function IssuesPage() {
  const t = await getTranslations("issuesPage");

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        {t("heading")}
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        {t("intro")}
      </p>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-amber-900 mb-2">
          {t("comingSoon")}
        </h2>
        <p className="text-amber-800">
          {t("comingSoonBody")}
        </p>
      </div>

      <Link
        href="/"
        className="text-primary-600 hover:text-primary-700 font-medium text-sm"
      >
        ← School Map
      </Link>
    </div>
  );
}
