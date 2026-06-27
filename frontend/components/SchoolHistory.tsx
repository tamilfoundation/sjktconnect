"use client";

/**
 * Sprint 31 (2026-06-27): School history / origin story.
 *
 * Three render states:
 *   1. Empty   — no history in any locale. Show contribution CTA.
 *   2. UNVERIFIED — content present (drawn from public sources e.g. Wikipedia).
 *                   Show amber disclaimer banner + sources line.
 *   3. SCHOOL_REVIEWED / VERIFIED — content present, school-approved.
 *                                   No disclaimer. Show "Verified" badge for VERIFIED.
 *                                   Show "Updated by school admin · <date>" footer.
 *
 * Per-locale: text picked by current locale (en/ms/ta); falls back to en if
 * current locale empty; shows "translate this" CTA when fallback in use.
 */

import { useTranslations, useLocale } from "next-intl";

interface SchoolHistoryProps {
  schoolName: string;
  history: { en?: string; ms?: string; ta?: string };
  historySourceUrls: string[];
  historyStatus: "UNVERIFIED" | "SCHOOL_REVIEWED" | "VERIFIED";
  historyUpdatedAt: string | null;
}

type Locale = "en" | "ms" | "ta";

function pickText(
  history: { en?: string; ms?: string; ta?: string },
  locale: Locale,
): { text: string; fellBackToEn: boolean } {
  const native = history[locale];
  if (native && native.trim()) return { text: native, fellBackToEn: false };
  const en = history.en;
  if (en && en.trim()) return { text: en, fellBackToEn: locale !== "en" };
  return { text: "", fellBackToEn: false };
}

function sourceLabel(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.endsWith("wikipedia.org")) {
      const lang = host.split(".")[0]; // "en" / "ms" / "ta"
      return `Wikipedia (${lang})`;
    }
    return host;
  } catch {
    return url;
  }
}

export default function SchoolHistory({
  schoolName,
  history,
  historySourceUrls,
  historyStatus,
  historyUpdatedAt,
}: SchoolHistoryProps) {
  const t = useTranslations("schoolHistory");
  const locale = useLocale() as Locale;
  const { text, fellBackToEn } = pickText(history, locale);

  // State 1: empty — placeholder + contribution CTA
  if (!text) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("emptyHeading")}
        </h2>
        <p className="text-sm text-gray-500 mb-4">{t("emptyIntro")}</p>
        <p className="text-sm text-gray-600">{t("emptyBody")}</p>
        <a
          href={`mailto:info@tamilfoundation.org?subject=${encodeURIComponent(`School History — ${schoolName}`)}`}
          className="inline-block mt-4 text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          {t("emptyContactCta")}
        </a>
      </div>
    );
  }

  // States 2 + 3: content present
  const showDisclaimer = historyStatus === "UNVERIFIED";
  const isVerified = historyStatus === "VERIFIED";

  // Render paragraphs (split on double newline; fall back to single para)
  const paragraphs = text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-800">
          {t("populatedHeading", { name: schoolName })}
        </h2>
        {isVerified && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
            {t("statusVerified")}
          </span>
        )}
      </div>

      {showDisclaimer && (
        <div className="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mb-4 flex items-start gap-2">
          <svg className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-amber-900 leading-relaxed">
            <strong>{t("disclaimerLabel")}</strong>{" "}
            {t("disclaimerBody")}{" "}
            <a
              href={`mailto:info@tamilfoundation.org?subject=${encodeURIComponent(`History correction — ${schoolName}`)}`}
              className="font-medium text-amber-900 underline hover:text-amber-700"
            >
              {t("disclaimerCta")}
            </a>
          </p>
        </div>
      )}

      {fellBackToEn && (
        <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2 mb-4">
          <p className="text-xs text-blue-900">
            {t("fellBackToEnBody")}{" "}
            <a
              href={`mailto:info@tamilfoundation.org?subject=${encodeURIComponent(`Translation — ${schoolName} (${locale})`)}`}
              className="font-medium underline hover:text-blue-700"
            >
              {t("fellBackToEnCta")}
            </a>
          </p>
        </div>
      )}

      <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      {historySourceUrls.length > 0 && (
        <div className="mt-5 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500">
            <span className="font-medium">{t("sourcesLabel")}:</span>{" "}
            {historySourceUrls.map((url, i) => (
              <span key={url}>
                {i > 0 && " · "}
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:text-primary-800 underline"
                >
                  {sourceLabel(url)}
                </a>
              </span>
            ))}
          </p>
        </div>
      )}

      {historyUpdatedAt && historyStatus !== "UNVERIFIED" && (
        <p className="mt-2 text-xs text-gray-400">
          {t("updatedFooter")} ·{" "}
          {new Date(historyUpdatedAt).toLocaleDateString(locale, {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}
        </p>
      )}
    </div>
  );
}
