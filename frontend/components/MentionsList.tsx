"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ConstituencyMention, HansardMention } from "@/lib/types";

const PAGE_SIZE_OPTIONS = [5, 10, 25];

type MentionItem = HansardMention | ConstituencyMention;

interface MentionsListProps {
  mentions: MentionItem[];
  showSchools?: boolean;
  title?: string;
}

function isHansardMention(m: MentionItem): m is HansardMention {
  return "schools" in m;
}

function sentimentConfig(sentiment: string | undefined) {
  switch (sentiment) {
    case "POSITIVE": return { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", label: "Positive" };
    case "NEGATIVE": return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Negative" };
    case "MIXED": return { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", label: "Mixed" };
    default: return { bg: "bg-gray-50", text: "text-gray-500", dot: "bg-gray-400", label: "Neutral" };
  }
}

function mentionTypeConfig(type: string | undefined) {
  switch (type?.toUpperCase()) {
    case "QUESTION": return { bg: "bg-blue-50", text: "text-blue-700" };
    case "DEBATE": return { bg: "bg-purple-50", text: "text-purple-700" };
    case "REPLY": return { bg: "bg-teal-50", text: "text-teal-700" };
    case "STATEMENT": return { bg: "bg-indigo-50", text: "text-indigo-700" };
    default: return { bg: "bg-gray-50", text: "text-gray-600" };
  }
}

export default function MentionsList({ mentions, showSchools = false, title }: MentionsListProps) {
  const t = useTranslations("parliamentWatch");
  const [pageSize, setPageSize] = useState(5);
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(mentions.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = mentions.slice(startIndex, startIndex + pageSize);

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  if (mentions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">
          {title || t("hansardMentions")}
        </h2>
        <p className="text-sm text-gray-500">{t("noMentionsYet")}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="text-xl font-bold text-gray-900">
          {title || t("hansardMentions")}
        </h2>
        <span className="text-sm text-gray-400">
          {mentions.length} {t("totalMentionsCount")}
        </span>
      </div>

      <div className="space-y-3">
        {paged.map((mention, index) => {
          const sentiment = "sentiment" in mention ? sentimentConfig(mention.sentiment) : null;
          const mentionType = mentionTypeConfig(mention.mention_type);

          return (
            <article
              key={isHansardMention(mention) ? mention.id : `${mention.sitting_date}-${index}`}
              className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 transition-shadow hover:shadow-md"
            >
              {/* Top row: date + tags */}
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <time className="text-xs font-medium text-gray-400">
                  {new Date(mention.sitting_date).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </time>
                {mention.mention_type && (
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${mentionType.bg} ${mentionType.text}`}>
                    {mention.mention_type}
                  </span>
                )}
                {mention.significance && mention.significance >= 3 && (
                  <span className="text-xs font-medium bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
                    {"★".repeat(Math.min(mention.significance, 5))}
                  </span>
                )}
                {sentiment && "sentiment" in mention && mention.sentiment && (
                  <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${sentiment.bg} ${sentiment.text}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${sentiment.dot}`} />
                    {sentiment.label}
                  </span>
                )}
              </div>

              {/* MP info */}
              {mention.mp_name && (
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0">
                    {mention.mp_name.charAt(0)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {mention.mp_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {[mention.mp_constituency, mention.mp_party].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                </div>
              )}

              {/* Summary */}
              <p className="text-sm text-gray-700 leading-relaxed">
                {mention.ai_summary}
              </p>

              {/* School tags */}
              {showSchools && isHansardMention(mention) && mention.schools.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {mention.schools.map((school) => (
                    <Link
                      key={school.moe_code}
                      href={`/school/${school.moe_code}`}
                      className="text-xs font-medium bg-primary-50 text-primary-700 px-2.5 py-1 rounded-full hover:bg-primary-100 transition-colors"
                    >
                      {school.name}
                    </Link>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>

      {/* Pagination */}
      <div className="mt-6 space-y-3">
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
              className="border border-gray-300 rounded-lg px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
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
