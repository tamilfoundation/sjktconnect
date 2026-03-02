import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("parliamentWatch");
  return {
    title: t("title"),
    description: t("intro"),
  };
}

export default async function ParliamentWatchPage() {
  const t = await getTranslations("parliamentWatch");

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        {t("heading")}
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        {t("intro")}
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-2">
          {t("comingSoon")}
        </h2>
        <p className="text-blue-800">
          {t("comingSoonBody")}{" "}
          <Link href="/" className="underline font-medium">
            {t("schoolMap")}
          </Link>{" "}
          {t("and")}{" "}
          <Link href="/constituencies" className="underline font-medium">
            {t("constituencyPages")}
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
