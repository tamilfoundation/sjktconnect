"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { SchoolMention } from "@/lib/types";
import PaginationBar from "./PaginationBar";

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
        <PaginationBar
          currentPage={safePage}
          totalPages={totalPages}
          totalItems={mentions.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={handlePageSizeChange}
          showingLabel={(from, to, total) => t("showingCount", { from, to, total })}
        />
      )}
    </div>
  );
}
