"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function SchoolNotFound() {
  const t = useTranslations("schoolProfile");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        {t("notFound")}
      </h1>
      <p className="text-gray-600 mb-6">
        {t("notFoundDescription")}
      </p>
      <Link
        href="/"
        className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
      >
        {t("backToMap")}
      </Link>
    </div>
  );
}
