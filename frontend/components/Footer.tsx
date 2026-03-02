"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function Footer() {
  const t = useTranslations("footer");

  return (
    <footer className="bg-white border-t border-gray-200 py-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-gray-500">
            {t("copyright", { year: new Date().getFullYear() })}
          </p>
          <Link
            href="/subscribe"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            {t("subscribe")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
