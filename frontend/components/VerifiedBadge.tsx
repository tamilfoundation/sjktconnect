"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";

interface VerifiedBadgeProps {
  claimedAt: string | null;
  lastVerified: string | null;
}

/**
 * Shows a "Verified" badge next to the school name once the page has been
 * claimed by its admin. Click to expand a small tooltip with claim + verify
 * dates.
 */
export default function VerifiedBadge({
  claimedAt,
  lastVerified,
}: VerifiedBadgeProps) {
  const t = useTranslations("claim");
  const locale = useLocale();
  const [open, setOpen] = useState(false);

  if (!claimedAt) return null;

  const fmt = (iso: string) =>
    new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", day: "numeric" })
      .format(new Date(iso));

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-800 text-xs font-medium hover:bg-green-200 transition"
        aria-expanded={open}
      >
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        {t("verified")}
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-10 w-64 p-3 rounded-lg bg-white border border-gray-200 shadow-lg text-xs text-gray-700">
          <p className="mb-1">
            <span className="font-medium">{t("claimedOn")}</span>{" "}
            {fmt(claimedAt)}
          </p>
          {lastVerified && (
            <p>
              <span className="font-medium">{t("verifiedOn")}</span>{" "}
              {fmt(lastVerified)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
