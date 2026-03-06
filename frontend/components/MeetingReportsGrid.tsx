"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { MeetingReport } from "@/lib/types";

const CARDS_PER_PAGE = 4;

function extractHeadline(html: string): string | null {
  const match = html.match(/<h2[^>]*>(.*?)<\/h2>/i);
  if (!match) return null;
  const text = match[1].replace(/<[^>]*>/g, "").trim();
  const sectionHeadings = [
    "Key Findings",
    "MP Scorecard",
    "Executive Responses",
    "Policy Signals",
    "What to Watch",
  ];
  if (sectionHeadings.some((h) => text.includes(h))) return null;
  return text;
}

function extractBlurb(html: string): string {
  // Get the first meaningful paragraph from the report HTML
  const paragraphs = html.match(/<p[^>]*>(.*?)<\/p>/gi) || [];
  for (const p of paragraphs) {
    const text = p.replace(/<[^>]*>/g, "").trim();
    // Skip very short or empty paragraphs
    if (text.length > 40) {
      // Truncate to ~150 chars at word boundary
      if (text.length <= 150) return text;
      return text.slice(0, 150).replace(/\s+\S*$/, "") + "...";
    }
  }
  // Fallback to executive_summary
  return "";
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = {
    day: "numeric",
    month: "short",
    year: "numeric",
  };
  return `${s.toLocaleDateString("en-GB", opts)} – ${e.toLocaleDateString("en-GB", opts)}`;
}

interface Props {
  reports: MeetingReport[];
}

export default function MeetingReportsGrid({ reports }: Props) {
  const t = useTranslations("parliamentWatch");
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(reports.length / CARDS_PER_PAGE);
  const visible = reports.slice(
    page * CARDS_PER_PAGE,
    (page + 1) * CARDS_PER_PAGE
  );

  return (
    <section className="mb-10">
      <h2 className="text-xl font-bold text-gray-900 mb-1">
        {t("meetingReports")}
      </h2>
      <p className="text-sm text-gray-500 mb-5">{t("meetingReportsDesc")}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {visible.map((report) => {
          const headline = extractHeadline(report.report_html || "");
          const blurb =
            extractBlurb(report.report_html || "") ||
            report.executive_summary
              ?.replace(/<[^>]*>/g, "")
              .slice(0, 150)
              .replace(/\s+\S*$/, "") + "..." ||
            "";

          return (
            <Link
              key={report.id}
              href={`/parliament-watch/${report.id}`}
              className="group block bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all p-5"
            >
              <p className="text-xs text-gray-400 mb-1.5">
                {report.short_name} &middot;{" "}
                {formatDateRange(report.start_date, report.end_date)}
              </p>
              <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary-700 transition-colors mb-2 line-clamp-2">
                {headline || report.short_name}
              </h3>
              <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                {blurb}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {report.sitting_count} sittings &middot;{" "}
                  {report.total_mentions} mentions
                </span>
                <span className="text-sm font-medium text-primary-600 group-hover:text-primary-700">
                  {t("readReport")} &rarr;
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            &larr; Previous
          </button>
          <span className="text-sm text-gray-500">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next &rarr;
          </button>
        </div>
      )}
    </section>
  );
}
