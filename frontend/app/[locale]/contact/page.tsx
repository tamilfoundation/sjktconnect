import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Breadcrumb from "@/components/Breadcrumb";
import ContactForm from "@/components/ContactForm";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("contact");
  return {
    title: `${t("title")} | SJK(T) Connect`,
    description: t("pageDescription"),
  };
}

export default async function ContactPage() {
  const t = await getTranslations("contact");
  const tc = await getTranslations("common");

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <Breadcrumb items={[{ label: tc("home"), href: "/" }, { label: t("title") }]} />

      <h1 className="text-3xl font-bold text-gray-900 mt-6 mb-2">
        {t("title")}
      </h1>
      <p className="text-gray-600 mb-8">{t("subtitle")}</p>

      <ContactForm />

      <div className="mt-8 pt-6 border-t border-gray-200 text-center">
        <p className="text-sm text-gray-500">{t("directEmail")}</p>
        <a
          href="mailto:info@tamilfoundation.org"
          className="text-sm text-primary-600 hover:text-primary-800 font-medium"
        >
          info@tamilfoundation.org
        </a>
        <p className="text-xs text-gray-400 mt-2">{t("responseTime")}</p>
      </div>
    </div>
  );
}
