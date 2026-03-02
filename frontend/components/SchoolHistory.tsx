"use client";

import { useTranslations } from "next-intl";

export default function SchoolHistory() {
  const t = useTranslations("parliamentWatch");

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        {t("historyHeading")}
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        {t("historyIntro")}
      </p>
      <p className="text-sm text-gray-600">
        {t("historyBody")}
      </p>
      <a
        href="mailto:info@tamilfoundation.org?subject=School%20History%20Contribution"
        className="inline-block mt-4 text-sm font-medium text-primary-600 hover:text-primary-800"
      >
        {t("contactUs")}
      </a>
    </div>
  );
}
