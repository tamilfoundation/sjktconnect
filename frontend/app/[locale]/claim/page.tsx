import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import ClaimForm from "@/components/ClaimForm";
import Breadcrumb from "@/components/Breadcrumb";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("claim");
  return {
    title: `${t("title")} | SJK(T) Connect`,
    description: t("pageDescription"),
  };
}

export default async function ClaimPage() {
  const t = await getTranslations("claim");
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
          {t("title")}
        </h1>
        <p className="text-gray-600 mb-6">
          {t("intro")}
        </p>

        <ClaimForm />
      </div>

      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">
          {t("howItWorks")}
        </h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>{t("step1")}</li>
          <li>{t("step2")}</li>
          <li>{t("step3")}</li>
          <li>{t("step4")}</li>
        </ol>
      </div>
    </main>
  );
}
