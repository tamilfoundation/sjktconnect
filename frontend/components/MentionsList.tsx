"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ConstituencyMention, HansardMention } from "@/lib/types";
import PaginationBar from "./PaginationBar";

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
      <PaginationBar
        currentPage={safePage}
        totalPages={totalPages}
        totalItems={mentions.length}
        pageSize={pageSize}
        onPageChange={setCurrentPage}
        onPageSizeChange={handlePageSizeChange}
        showingLabel={(from, to, total) => t("showingCount", { from, to, total })}
      />
    </div>
  );
}
