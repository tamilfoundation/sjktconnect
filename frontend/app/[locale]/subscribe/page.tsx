import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import SubscribeForm from "@/components/SubscribeForm";
import Breadcrumb from "@/components/Breadcrumb";
import { buildAlternates } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations("subscribe");
  return {
    title: `${t("title")} | SJK(T) Connect`,
    description: t("intro"),
    alternates: buildAlternates("/subscribe", locale as "en" | "ta" | "ms"),
  };
}

export default async function SubscribePage() {
  const t = await getTranslations("subscribe");
  const tc = await getTranslations("common");

  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: tc("home"), href: "/" },
          { label: t("title") },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {t("heading")}
        </h1>
        <p className="text-gray-600 mb-6">
          {t("intro")}
        </p>

        <SubscribeForm />
      </div>

      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">
          {t("whatYouReceive")}
        </h2>
        <ul className="text-sm text-gray-600 space-y-2">
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">{t("parliamentWatch")}</span>
            {t("whenMps")}
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">{t("newsWatch")}</span>
            {t("mediaAlerts")}
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium text-primary-600">{t("monthlyBlast")}</span>
            {t("monthlyDigest")}
          </li>
        </ul>
      </div>
    </main>
  );
}
