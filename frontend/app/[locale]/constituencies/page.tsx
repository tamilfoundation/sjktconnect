import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { fetchConstituencies } from "@/lib/api";
import ConstituencyList from "@/components/ConstituencyList";

export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("constituency");
  return {
    title: t("pageTitle"),
    description: t("pageDescription"),
    openGraph: {
      title: t("pageTitle"),
      description: t("pageDescription"),
      type: "website",
      siteName: "SJK(T) Connect",
    },
  };
}

export default async function ConstituenciesPage() {
  const t = await getTranslations("constituency");
  const constituencies = await fetchConstituencies();

  // Extract unique states
  const states = Array.from(
    new Set(constituencies.map((c) => c.state))
  ).sort();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {t("countSubtitle", { count: constituencies.length })}
        </p>
      </div>

      <ConstituencyList
        constituencies={constituencies}
        states={states}
      />
    </div>
  );
}
