"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

interface ClaimButtonProps {
  moeCode: string;
}

export default function ClaimButton({ moeCode }: ClaimButtonProps) {
  const t = useTranslations("claim");

  return (
    <div className="bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-lg p-6 text-center">
      <h3 className="text-lg font-semibold text-primary-800 mb-2">
        {t("areYouFromSchool")}
      </h3>
      <p className="text-sm text-primary-700 mb-4">
        {t("verifyAndUpdate")}
      </p>
      <Link
        href={`/claim/?school=${moeCode}`}
        className="inline-block bg-primary-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors"
      >
        {t("claimThisPage")}
      </Link>
      <p className="text-xs text-primary-500 mt-2">
        {t("requiresMoeEmail")}
      </p>
    </div>
  );
}
