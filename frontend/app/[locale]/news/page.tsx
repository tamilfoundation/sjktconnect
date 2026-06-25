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
  // Sprint 27 #3: raised from 50 (Sprint 17 egress cap) to 250. The
  // initial paint still shows 10 per page; 250 widens what the
  // tab-filter + top-schools sidebar can compute over. The full search
  // path bypasses this cap by hitting the API live — see NewsList.
  const data = await fetchNews({ pageSize: 250 });

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
