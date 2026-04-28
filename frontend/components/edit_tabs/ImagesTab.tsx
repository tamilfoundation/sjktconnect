"use client";

/**
 * Images tab — links to the existing /dashboard/images manager
 * (Sprint 14). Kept lightweight; no CRUD here, just a launchpad.
 */

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

interface ImagesTabProps {
  moeCode: string;
}

export default function ImagesTab({ moeCode }: ImagesTabProps) {
  const t = useTranslations("schoolEdit");

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">{t("imagesIntro")}</p>
      <Link
        href={`/dashboard/images?school=${moeCode}`}
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        {t("imagesGoToManager")}
      </Link>
    </div>
  );
}
