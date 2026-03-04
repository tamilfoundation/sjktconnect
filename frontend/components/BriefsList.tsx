"use client";

import { useTranslations } from "next-intl";
import { SittingBrief } from "@/lib/types";

interface BriefsListProps {
  briefs: SittingBrief[];
}

/**
 * Strip HTML tags and return plain text summary.
 * The brief summary_html is generated server-side by our Gemini pipeline,
 * not from user input. We strip tags for safety rather than rendering HTML.
 */
function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export default function BriefsList({ briefs }: BriefsListProps) {
  const t = useTranslations("parliamentWatch");

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        {t("sittingBriefs")}
      </h2>
      <div className="space-y-4">
        {briefs.map((brief) => (
          <div
            key={brief.id}
            className="border-l-4 border-primary-400 pl-4 py-3"
          >
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-800">
                {brief.title}
              </h3>
              <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded">
                {brief.mention_count} {t("mentionsLabel")}
              </span>
            </div>
            <p className="text-sm text-gray-700 line-clamp-4">
              {stripHtml(brief.summary_html)}
            </p>
            <p className="text-xs text-gray-400 mt-2">
              {new Date(brief.sitting_date).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
