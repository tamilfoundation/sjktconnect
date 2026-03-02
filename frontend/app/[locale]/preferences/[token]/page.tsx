import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import PreferencesForm from "@/components/PreferencesForm";
import Breadcrumb from "@/components/Breadcrumb";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("subscribe");
  return {
    title: `${t("preferencesTitle")} | SJK(T) Connect`,
    description: t("chooseTypes"),
  };
}

interface PreferencesPageProps {
  params: Promise<{ token: string }>;
}

export default async function PreferencesPage({ params }: PreferencesPageProps) {
  const { token } = await params;
  const t = await getTranslations("subscribe");
  const tc = await getTranslations("common");

  return (
    <main className="max-w-lg mx-auto px-4 py-8">
      <Breadcrumb
        items={[
          { label: tc("home"), href: "/" },
          { label: t("preferencesTitle") },
        ]}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {t("subscriptionPrefs")}
        </h1>
        <p className="text-gray-600 mb-6">
          {t("chooseTypes")}
        </p>

        <PreferencesForm token={token} />
      </div>
    </main>
  );
}
