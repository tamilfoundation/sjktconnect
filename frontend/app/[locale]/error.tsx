"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function LocaleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errorBoundary");

  useEffect(() => {
    console.error("LocaleError boundary caught:", error);
  }, [error]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{t("title")}</h1>
      <p className="text-gray-600 mb-8">{t("description")}</p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={reset}
          className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
        >
          {t("retry")}
        </button>
        <Link
          href="/"
          className="inline-block bg-white border border-gray-300 text-gray-700 font-medium px-6 py-3 rounded-lg hover:bg-gray-50 transition-colors"
        >
          {t("home")}
        </Link>
      </div>
      {error.digest && (
        <p className="mt-8 text-xs text-gray-400 font-mono">ref: {error.digest}</p>
      )}
    </div>
  );
}
