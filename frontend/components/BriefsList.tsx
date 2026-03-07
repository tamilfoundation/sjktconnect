"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { SittingBrief } from "@/lib/types";
import PaginationBar from "./PaginationBar";

interface BriefsListProps {
  briefs: SittingBrief[];
}

/**
 * Extract the lead paragraph from the HTML for the collapsed preview.
 * Takes content before the first heading (h2 or h3), which is the blurb.
 */
function extractSummary(html: string): string {
  // Get content before the first heading (h2 or h3)
  const match = html.match(/^([\s\S]*?)(?=<h[23]>)/i);
  if (match && match[1].trim()) {
    const plain = match[1].replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    if (plain.length > 0) {
      return plain.length > 300 ? plain.slice(0, 297) + "..." : plain;
    }
  }
  // Fallback: strip all tags and take first 300 chars
  const plain = html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  return plain.length > 300 ? plain.slice(0, 297) + "..." : plain;
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

              {/* Toggle button + detail link */}
              <div className="px-6 py-3 border-t border-gray-100 flex items-center gap-4">
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
                <a
                  href={`/parliament-watch/sittings/${brief.id}`}
                  className="text-sm text-gray-400 hover:text-primary-600 transition-colors flex items-center gap-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  {t("viewBriefDetail")}
                </a>
              </div>
            </article>
          );
        })}
      </div>

      {/* Pagination */}
      {briefs.length > 5 && (
        <PaginationBar
          currentPage={safePage}
          totalPages={totalPages}
          totalItems={briefs.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
          showingLabel={(from, to, total) => t("showingCount", { from, to, total })}
        />
      )}
    </div>
  );
}
