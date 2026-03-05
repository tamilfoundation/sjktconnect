"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { SchoolMention } from "@/lib/types";

const PAGE_SIZE_OPTIONS = [5, 10, 25];

interface MentionsSectionProps {
  mentions: SchoolMention[];
}

export default function MentionsSection({ mentions }: MentionsSectionProps) {
  const t = useTranslations("parliamentWatch");
  const [pageSize, setPageSize] = useState(5);
  const [currentPage, setCurrentPage] = useState(1);

  if (mentions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("heading")}
        </h2>
        <p className="text-sm text-gray-500 mb-3">
          {t("noMentionsSubscribe")}
        </p>
        <Link
          href="/subscribe"
          className="inline-block text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {t("subscribeCta")} →
        </Link>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(mentions.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = mentions.slice(startIndex, startIndex + pageSize);

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="text-lg font-semibold text-gray-800">
          {t("heading")}
        </h2>
        <span className="text-sm text-gray-400">
          {mentions.length} {t("totalMentionsCount")}
        </span>
      </div>

      <div className="space-y-4">
        {paged.map((mention, index) => (
          <div
            key={`${mention.sitting_date}-${index}`}
            className="border-l-4 border-primary-400 pl-4 py-2"
          >
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="text-sm font-medium text-gray-800">
                {mention.mp_name}
              </span>
              {mention.mp_party && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                  {mention.mp_party}
                </span>
              )}
              {mention.significance && (
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    mention.significance >= 4
                      ? "bg-green-100 text-green-700"
                      : mention.significance >= 2
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {t("significance", { score: mention.significance })}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 mb-1">{mention.ai_summary}</p>
            <div className="text-xs text-gray-400">
              {new Date(mention.sitting_date).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
              {mention.mention_type && ` · ${mention.mention_type}`}
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {mentions.length > 5 && (
        <div className="mt-5 pt-4 border-t border-gray-100 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500">
            <span>
              {t("showingCount", {
                from: startIndex + 1,
                to: Math.min(startIndex + pageSize, mentions.length),
                total: mentions.length,
              })}
            </span>
            <div className="flex items-center gap-2">
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="border border-gray-300 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
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
                  <span key={`ellipsis-${i}`} className="px-2 py-2 text-sm text-gray-400">
                    ...
                  </span>
                ) : (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page as number)}
                    className={`w-9 h-9 text-sm font-medium rounded-lg transition-colors ${
                      safePage === page
                        ? "bg-primary-600 text-white"
                        : "text-gray-600 hover:bg-gray-100"
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

function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: (number | "...")[] = [1];
  if (current > 3) pages.push("...");
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
}
