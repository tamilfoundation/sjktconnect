import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import DonationForm from "@/components/DonationForm";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("donate");
  return {
    title: `${t("pageTitle")} | SJK(T) Connect`,
    description: t("pageDescription"),
  };
}

export default async function DonatePage() {
  const t = await getTranslations("donate");

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="text-lg text-gray-600 mt-3">{t("subtitle")}</p>
      </div>

      {/* Donation Form Card */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 sm:p-8">
        <DonationForm />
      </div>

      {/* School donation CTA */}
      <div className="mt-8 text-center bg-blue-50 rounded-lg p-6">
        <p className="text-gray-700 mb-3">{t("schoolDonationCta")}</p>
        <Link
          href="/"
          className="inline-block px-6 py-2 text-sm font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
        >
          {t("findSchool")}
        </Link>
      </div>
    </div>
  );
}
