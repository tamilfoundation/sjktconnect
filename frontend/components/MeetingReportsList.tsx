"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { MeetingReport } from "@/lib/types";
import PaginationBar from "./PaginationBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MeetingReportsListProps {
  reports: MeetingReport[];
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

export default function MeetingReportsList({ reports }: MeetingReportsListProps) {
  const t = useTranslations("parliamentWatch");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [pageSize, setPageSize] = useState(5);
  const [currentPage, setCurrentPage] = useState(1);

  if (reports.length === 0) return null;

  const totalPages = Math.max(1, Math.ceil(reports.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = reports.slice(startIndex, startIndex + pageSize);

  return (
    <div className="mb-8">
      <h2 className="text-xl font-bold text-gray-900 mb-1">
        {t("meetingReports")}
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        {t("meetingReportsDesc")}
      </p>
      <div className="space-y-4">
        {paged.map((report) => {
          const isExpanded = expandedId === report.id;
          return (
            <article
              key={report.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden transition-shadow hover:shadow-md"
            >
              {/* Header */}
              <div className="px-6 pt-5 pb-3">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-primary-600 uppercase tracking-wide mb-1">
                      {formatDateRange(report.start_date, report.end_date)}
                    </p>
                    <h3 className="text-base font-semibold text-gray-900 leading-snug">
                      {report.short_name}
                    </h3>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <span className="inline-flex items-center gap-1 text-xs font-medium bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      {report.sitting_count} {t("sittingsTracked").toLowerCase()}
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      {report.total_mentions} {t("totalMentionsCount")}
                    </span>
                  </div>
                </div>

                {/* Executive summary preview (collapsed) — sanitised server-side HTML */}
                {!isExpanded && report.executive_summary && (
                  <div
                    className="text-sm text-gray-600 leading-relaxed line-clamp-3 mt-2 [&>p]:inline"
                    dangerouslySetInnerHTML={{ __html: report.executive_summary }}
                  />
                )}
              </div>

              {/* Full report (expanded) — server-generated HTML from trusted Gemini pipeline */}
              {isExpanded && (
                <div className="px-6 pb-2">
                  {/* Editorial illustration */}
                  {report.illustration_url && (
                    <div className="flex justify-center my-4">
                      <img
                        src={report.illustration_url}
                        alt={`Editorial illustration for ${report.short_name}`}
                        className="max-w-xs rounded-lg border border-gray-200 shadow-sm"
                      />
                    </div>
                  )}
                  <div
                    className="prose prose-sm max-w-none
                      prose-headings:text-gray-900 prose-headings:font-semibold
                      prose-h2:text-base prose-h2:mt-4 prose-h2:mb-2
                      prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1.5
                      prose-p:text-gray-700 prose-p:leading-relaxed
                      prose-li:text-gray-700 prose-li:leading-relaxed
                      prose-strong:text-gray-900
                      prose-ul:my-1.5 prose-li:my-0.5
                      prose-table:text-sm prose-th:text-left prose-th:px-3 prose-th:py-1.5
                      prose-td:px-3 prose-td:py-1.5 prose-table:border-collapse
                      prose-th:bg-gray-50 prose-th:border-b prose-th:border-gray-200
                      prose-td:border-b prose-td:border-gray-100"
                    dangerouslySetInnerHTML={{ __html: report.report_html }}
                  />
                </div>
              )}

              {/* Share & Download bar (expanded only) */}
              {isExpanded && (
                <div className="px-6 py-3 border-t border-gray-100 flex flex-wrap items-center gap-3">
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Share</span>
                  <ShareButton
                    platform="whatsapp"
                    text={report.social_post_text}
                    url={`https://tamilschool.org/parliament-watch`}
                  />
                  <ShareButton
                    platform="x"
                    text={report.social_post_text}
                    url={`https://tamilschool.org/parliament-watch`}
                  />
                  <ShareButton
                    platform="facebook"
                    url={`https://tamilschool.org/parliament-watch`}
                  />
                  <CopyLinkButton url={`https://tamilschool.org/parliament-watch`} />
                  <a
                    href={`${API_URL}/api/v1/meetings/${report.id}/download/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto inline-flex items-center gap-1.5 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download PDF
                  </a>
                </div>
              )}

              {/* Toggle button */}
              <div className="px-6 py-3 border-t border-gray-100">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : report.id)}
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
      {reports.length > 5 && (
        <PaginationBar
          currentPage={safePage}
          totalPages={totalPages}
          totalItems={reports.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
          showingLabel={(from, to, total) => t("showingCount", { from, to, total })}
        />
      )}
    </div>
  );
}

/* --- Helper components --- */

const PLATFORM_CONFIG = {
  whatsapp: {
    label: "WhatsApp",
    color: "bg-green-600 hover:bg-green-700",
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
      </svg>
    ),
  },
  x: {
    label: "X",
    color: "bg-black hover:bg-gray-800",
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  facebook: {
    label: "Facebook",
    color: "bg-blue-600 hover:bg-blue-700",
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
  },
} as const;

function ShareButton({
  platform,
  text,
  url,
}: {
  platform: keyof typeof PLATFORM_CONFIG;
  text?: string;
  url: string;
}) {
  const config = PLATFORM_CONFIG[platform];
  const shareText = text ? `${text}\n\n` : "";

  const shareUrls = {
    whatsapp: `https://wa.me/?text=${encodeURIComponent(shareText + url)}`,
    x: `https://x.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(url)}`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
  };

  return (
    <a
      href={shareUrls[platform]}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 text-xs font-medium text-white ${config.color} px-2.5 py-1.5 rounded-lg transition-colors`}
      title={`Share on ${config.label}`}
    >
      {config.icon}
      {config.label}
    </a>
  );
}

function CopyLinkButton({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 px-2.5 py-1.5 rounded-lg transition-colors"
      title="Copy link"
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        {copied ? (
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        )}
      </svg>
      {copied ? "Copied!" : "Copy Link"}
    </button>
  );
}
