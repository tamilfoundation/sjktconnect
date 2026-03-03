import { Metadata } from "next";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("about");
  return {
    title: `${t("title")} | SJK(T) Connect`,
    description: t("pageDescription"),
  };
}

export default async function AboutPage() {
  const t = await getTranslations("about");

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="text-lg text-gray-600 mt-3">{t("subtitle")}</p>
      </div>

      {/* What We Do */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t("whatWeDoTitle")}
        </h2>
        <p className="text-gray-700 leading-relaxed mb-4">{t("whatWeDoP1")}</p>
        <p className="text-gray-700 leading-relaxed">{t("whatWeDoP2")}</p>
      </section>

      {/* Feature Cards */}
      <section className="mb-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            }
            title={t("featureParliament")}
            description={t("featureParliamentDesc")}
          />
          <FeatureCard
            icon={
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
            }
            title={t("featureNews")}
            description={t("featureNewsDesc")}
          />
          <FeatureCard
            icon={
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            }
            title={t("featureDirectory")}
            description={t("featureDirectoryDesc")}
          />
        </div>
      </section>

      {/* About Tamil Foundation */}
      <section className="mb-12 bg-blue-50 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t("aboutTFTitle")}
        </h2>
        <p className="text-gray-700 leading-relaxed mb-4">
          {t("aboutTFBody")}
        </p>
        <p className="text-gray-600">
          <a
            href={`mailto:${t("contactEmail")}`}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            {t("contactEmail")}
          </a>
        </p>
      </section>

      {/* Data Sources */}
      <section className="border-t pt-8">
        <h2 className="text-lg font-semibold text-gray-700 mb-2">
          {t("dataSourceTitle")}
        </h2>
        <p className="text-sm text-gray-500">{t("dataSourceBody")}</p>
      </section>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-white border rounded-lg p-6 shadow-sm">
      <div className="text-blue-900 mb-3">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
