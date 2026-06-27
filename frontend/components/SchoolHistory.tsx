"use client";

/**
 * School history / origin story.
 *
 * Render states:
 *   1. Empty — no history in any locale. Contribution CTA.
 *   2. Populated — pills (key dates) + prose paragraphs + contextual
 *      provenance footer ("Source: X — not yet verified. Help improve →"
 *      when UNVERIFIED, or "Drawn from public sources — not yet verified"
 *      when status is UNVERIFIED but no source URL recorded).
 *      SCHOOL_REVIEWED / VERIFIED suppress the "not verified" suffix and
 *      VERIFIED adds a small badge by the heading.
 *
 * Per-locale: text + key_dates picked by current locale (en/ms/ta);
 * falls back to en if current locale empty.
 */

import { useTranslations, useLocale } from "next-intl";

interface SchoolHistoryProps {
  schoolName: string;
  history: { en?: string; ms?: string; ta?: string };
  historySourceUrls: string[];
  historyStatus: "UNVERIFIED" | "SCHOOL_REVIEWED" | "VERIFIED";
  historyUpdatedAt: string | null;
  historyKeyDates?: { en?: string[]; ms?: string[]; ta?: string[] };
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

function pickKeyDates(
  keyDates: { en?: string[]; ms?: string[]; ta?: string[] } | undefined,
  locale: Locale,
): string[] {
  if (!keyDates) return [];
  const native = keyDates[locale];
  if (native && native.length) return native;
  return keyDates.en || [];
}

function sourceLabel(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    if (host.endsWith("wikipedia.org")) {
      const lang = host.split(".")[0];
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
  historyKeyDates,
}: SchoolHistoryProps) {
  const t = useTranslations("schoolHistory");
  const locale = useLocale() as Locale;
  const { text, fellBackToEn } = pickText(history, locale);
  const keyDates = pickKeyDates(historyKeyDates, locale);

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

  const isUnverified = historyStatus === "UNVERIFIED";
  const isVerified = historyStatus === "VERIFIED";
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

      {keyDates.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-4">
          {keyDates.map((d, i) => (
            <span
              key={i}
              className="inline-block text-[11px] font-medium text-primary-700 bg-primary-50 border border-primary-100 px-2 py-0.5 rounded-full"
            >
              {d}
            </span>
          ))}
        </div>
      )}

      <div className="mt-5 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-500">
          {historySourceUrls.length > 0 ? (
            <>
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
            </>
          ) : (
            isUnverified && <span>{t("disclaimerNoSource")}</span>
          )}
          {isUnverified && (
            <>
              {" — "}
              <a
                href={`mailto:info@tamilfoundation.org?subject=${encodeURIComponent(`History correction — ${schoolName}`)}`}
                className="text-primary-600 hover:text-primary-800 underline"
              >
                {t("helpImprove")}
              </a>
            </>
          )}
          {historyUpdatedAt && !isUnverified && (
            <>
              {historySourceUrls.length > 0 ? " · " : ""}
              {t("updatedFooter")}{" "}
              {new Date(historyUpdatedAt).toLocaleDateString(
                locale === "ms" ? "ms-MY" : locale === "ta" ? "ta-MY" : "en-MY",
                { year: "numeric", month: "long", day: "numeric" },
              )}
            </>
          )}
        </p>
      </div>
    </div>
  );
}
