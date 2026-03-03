import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { fetchNews } from "@/lib/api";
import NewsList from "@/components/NewsList";

export const revalidate = 300; // 5 minutes

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("news");
  return {
    title: t("pageTitle"),
    description: t("intro"),
    openGraph: {
      title: t("pageTitle"),
      description: t("intro"),
      type: "website",
      siteName: "SJK(T) Connect",
    },
  };
}

export default async function NewsPage() {
  const t = await getTranslations("news");
  const data = await fetchNews({ pageSize: 50 });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {t("heading")}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {t("intro")}
        </p>
      </div>

      <NewsList articles={data.results} totalCount={data.count} />
    </div>
  );
}
