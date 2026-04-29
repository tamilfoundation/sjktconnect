import { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { fetchNews } from "@/lib/api";
import NewsList from "@/components/NewsList";
import { buildAlternates } from "@/lib/seo";

export const revalidate = 86400;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
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
    alternates: buildAlternates("/news", locale as "en" | "ta" | "ms"),
  };
}

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default async function NewsPage({ params }: PageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("news");
  // Sprint 17: was pageSize: 500 (~138 KB on every render). 50 is plenty
  // for the initial paint; NewsList already shows totalCount and can paginate.
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
