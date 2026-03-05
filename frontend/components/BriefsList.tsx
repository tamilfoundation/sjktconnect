"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { SittingBrief } from "@/lib/types";

interface BriefsListProps {
  briefs: SittingBrief[];
}

/**
 * Extract just the Summary paragraph from the HTML for the collapsed preview.
 * Looks for content between the first <h2>Summary</h2> and the next <h2>.
 */
function extractSummary(html: string): string {
  // Get text after "Summary" heading up to the next heading
  const match = html.match(/<h2>Summary<\/h2>\s*([\s\S]*?)(?=<h2>|$)/i);
  if (match) {
    return match[1].replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  }
  // Fallback: strip all tags and take first 300 chars
  const plain = html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  return plain.length > 300 ? plain.slice(0, 300) + "..." : plain;
}

const PAGE_SIZE_OPTIONS = [5, 10, 25];

function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | "...")[] = [1];
  if (current > 3) pages.push("...");
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
}

export default function BriefsList({ briefs }: BriefsListProps) {
  const t = useTranslations("parliamentWatch");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(5);
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(briefs.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = briefs.slice(startIndex, startIndex + pageSize);

  return (
    <div className="mb-8">
      <h2 className="text-xl font-bold text-gray-900 mb-1">
        {t("sittingBriefs")}
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        {t("sittingBriefsDesc")}
      </p>
      <div className="space-y-4">
        {paged.map((brief) => {
          const isExpanded = expandedId === brief.id;
          return (
            <article
              key={brief.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden transition-shadow hover:shadow-md"
            >
              {/* Header */}
              <div className="px-6 pt-5 pb-3">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-primary-600 uppercase tracking-wide mb-1">
                      {new Date(brief.sitting_date).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                    </p>
                    <h3 className="text-base font-semibold text-gray-900 leading-snug">
                      {brief.title.replace(/\s*[—–-]\s*\d{1,2}\s+\w+\s+\d{4}$/, "")}
                    </h3>
                  </div>
                  <span className="shrink-0 inline-flex items-center gap-1 text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    {brief.mention_count} {brief.mention_count === 1 ? "mention" : "mentions"}
                  </span>
                </div>

                {/* Summary preview (always visible) */}
                {!isExpanded && (
                  <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 mt-2">
                    {extractSummary(brief.summary_html)}
                  </p>
                )}
              </div>

              {/* Full report (expanded) */}
              {isExpanded && (
                <div
                  className="px-6 pb-2 prose prose-sm max-w-none
                    prose-headings:text-gray-900 prose-headings:font-semibold
                    prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2
                    prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1.5
                    prose-p:text-gray-700 prose-p:leading-relaxed
                    prose-li:text-gray-700 prose-li:leading-relaxed
                    prose-strong:text-gray-900
                    prose-ul:my-1.5 prose-li:my-0.5"
                  dangerouslySetInnerHTML={{ __html: brief.summary_html }}
                />
              )}

              {/* Toggle button */}
              <div className="px-6 py-3 border-t border-gray-100">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : brief.id)}
                  className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors flex items-center gap-1"
                >
                  {isExpanded ? t("collapseReport") : t("readFullReport")}
                  <svg
                    className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {/* Pagination */}
      {briefs.length > 5 && (
        <div className="mt-6 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500">
            <span>
              {t("showingCount", {
                from: startIndex + 1,
                to: Math.min(startIndex + pageSize, briefs.length),
                total: briefs.length,
              })}
            </span>
            <div className="flex items-center gap-2">
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
              <span className="text-gray-400">{t("perPage")}</span>
            </div>
          </div>

          {totalPages > 1 && (
            <nav aria-label="Pagination" className="flex items-center justify-center gap-1">
              <button
                onClick={() => setCurrentPage(safePage - 1)}
                disabled={safePage === 1}
                className="px-3 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100"
              >
                {t("previous")}
              </button>
              {getPageNumbers(safePage, totalPages).map((page, i) =>
                page === "..." ? (
                  <span key={`ellipsis-${i}`} className="px-2 py-2 text-sm text-gray-400">...</span>
                ) : (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page as number)}
                    className={`w-9 h-9 text-sm font-medium rounded-lg transition-colors ${
                      safePage === page ? "bg-primary-600 text-white" : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {page}
                  </button>
                )
              )}
              <button
                onClick={() => setCurrentPage(safePage + 1)}
                disabled={safePage === totalPages}
                className="px-3 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100"
              >
                {t("next")}
              </button>
            </nav>
          )}
        </div>
      )}
    </div>
  );
}
