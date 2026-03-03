import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Breadcrumb from "@/components/Breadcrumb";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legal");
  return {
    title: `${t("cookiesTitle")} | SJK(T) Connect`,
  };
}

export default async function CookiesPage() {
  const t = await getTranslations("legal");
  const tc = await getTranslations("common");

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Breadcrumb items={[{ label: tc("home"), href: "/" }, { label: t("cookiesTitle") }]} />

      <h1 className="text-3xl font-bold text-gray-900 mt-6 mb-8">
        {t("cookiesTitle")}
      </h1>
      <p className="text-sm text-gray-500 mb-8">{t("lastUpdated")}</p>

      <div className="prose prose-gray max-w-none space-y-8">
        <Section title={t("cookiesIntroTitle")}>
          <p>{t("cookiesIntroBody")}</p>
        </Section>

        <Section title={t("cookiesEssentialTitle")}>
          <p>{t("cookiesEssentialBody")}</p>
        </Section>

        <Section title={t("cookiesThirdPartyTitle")}>
          <p>{t("cookiesThirdPartyBody")}</p>
        </Section>

        <Section title={t("cookiesManageTitle")}>
          <p>{t("cookiesManageBody")}</p>
        </Section>

        <Section title={t("contactUsTitle")}>
          <p>{t("contactUsBody")}</p>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-xl font-semibold text-gray-800 mb-3">{title}</h2>
      <div className="text-gray-600 leading-relaxed">{children}</div>
    </section>
  );
}
