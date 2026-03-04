"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { NewsArticle } from "@/lib/types";
import NewsCard from "./NewsCard";

interface Props {
  articles: NewsArticle[];
  totalCount: number;
}

type Category = "all" | "school" | "general";

const PAGE_SIZE_OPTIONS = [5, 10, 25];

export default function NewsList({ articles, totalCount }: Props) {
  const t = useTranslations("news");
  const [activeTab, setActiveTab] = useState<Category>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    return articles.filter((article) => {
      if (activeTab === "school" && article.mentioned_schools.length === 0) return false;
      if (activeTab === "general" && article.mentioned_schools.length > 0) return false;

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          article.title.toLowerCase().includes(q) ||
          article.ai_summary.toLowerCase().includes(q) ||
          article.source_name.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [articles, activeTab, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = filtered.slice(startIndex, startIndex + pageSize);

  // Reset to page 1 when filters change
  const handleTabChange = (tab: Category) => {
    setActiveTab(tab);
    setCurrentPage(1);
  };
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  // Compute most mentioned schools
  const topSchools = useMemo(() => {
    const schoolCounts = new Map<string, { name: string; moe_code: string; count: number }>();
    articles.forEach((article) => {
      article.mentioned_schools.forEach((school) => {
        const existing = schoolCounts.get(school.moe_code);
        if (existing) {
          existing.count++;
        } else {
          schoolCounts.set(school.moe_code, { ...school, count: 1 });
        }
      });
    });
    return Array.from(schoolCounts.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [articles]);

  const tabs: { key: Category; label: string }[] = [
    { key: "all", label: t("tabAll") },
    { key: "school", label: t("tabBySchool") },
    { key: "general", label: t("tabGeneral") },
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-8">
      {/* Main content */}
      <div className="flex-1 min-w-0">
        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex rounded-lg border border-gray-200 overflow-hidden">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "bg-primary-600 text-white"
                    : "bg-white text-gray-700 hover:bg-gray-50"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 min-w-[200px] focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Article list */}
        {paged.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-sm">
              {searchQuery ? t("noArticlesFiltered") : t("noArticles")}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {paged.map((article) => (
              <NewsCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {filtered.length > 0 && (
          <div className="mt-6 space-y-3">
            {/* Top row: showing count + per-page selector */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500">
              <span>
                {t("showingCount", {
                  from: startIndex + 1,
                  to: Math.min(startIndex + pageSize, filtered.length),
                  total: filtered.length,
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

            {/* Page navigation */}
            {totalPages > 1 && (
              <Pagination
                currentPage={safePage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                prevLabel={t("previous")}
                nextLabel={t("next")}
                pageLabel={(page, total) => t("page", { page, totalPages: total })}
              />
            )}
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className="lg:w-80 shrink-0 space-y-6">
        <div className="bg-primary-50 rounded-lg p-5 border border-primary-100">
          <h3 className="text-sm font-semibold text-primary-800 mb-2">
            {t("subscribeCta")}
          </h3>
          <p className="text-xs text-primary-700 mb-3">
            {t("subscribeDesc")}
          </p>
          <Link
            href="/subscribe"
            className="inline-block bg-primary-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
          >
            {t("subscribeButton")}
          </Link>
        </div>

        {topSchools.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              {t("mostMentioned")}
            </h3>
            <ul className="space-y-2">
              {topSchools.map((school) => (
                <li key={school.moe_code}>
                  <Link
                    href={`/school/${school.moe_code}`}
                    className="text-sm text-primary-600 hover:text-primary-800 hover:underline"
                  >
                    {school.name}
                  </Link>
                  <span className="text-xs text-gray-400 ml-1">
                    ({school.count})
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Pagination component ─── */

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  prevLabel: string;
  nextLabel: string;
  pageLabel: (page: number, total: number) => string;
}

function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  prevLabel,
  nextLabel,
  pageLabel,
}: PaginationProps) {
  const pages = getPageNumbers(currentPage, totalPages);

  return (
    <nav aria-label="Pagination">
      {/* Desktop: full page numbers */}
      <div className="hidden sm:flex items-center justify-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100"
        >
          {prevLabel}
        </button>

        {pages.map((page, i) =>
          page === "..." ? (
            <span key={`ellipsis-${i}`} className="px-2 py-2 text-sm text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page as number)}
              className={`w-9 h-9 text-sm font-medium rounded-lg transition-colors ${
                currentPage === page
                  ? "bg-primary-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {page}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100"
        >
          {nextLabel}
        </button>
      </div>

      {/* Mobile: compact prev/page/next */}
      <div className="flex sm:hidden items-center justify-between">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-50"
        >
          {prevLabel}
        </button>

        <span className="text-sm text-gray-500">
          {pageLabel(currentPage, totalPages)}
        </span>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-50"
        >
          {nextLabel}
        </button>
      </div>
    </nav>
  );
}

/** Generate page numbers with ellipsis for large page counts */
function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | "...")[] = [1];

  if (current > 3) {
    pages.push("...");
  }

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) {
    pages.push("...");
  }

  pages.push(total);
  return pages;
}
