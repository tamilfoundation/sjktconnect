"use client";

import { useState, useMemo, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { NewsArticle } from "@/lib/types";
import { fetchNews } from "@/lib/api";
import { schoolPath } from "@/lib/urls";
import NewsCard from "./NewsCard";
import PaginationBar from "./PaginationBar";

interface Props {
  articles: NewsArticle[];
  totalCount: number;
}

type Category = "all" | "school" | "general";

// Sprint 27 #3: search now hits the API instead of client-filtering
// the initial 250. This widens search to ALL approved articles in the
// DB (currently ~111+ per month), not just what fit in the initial
// paint. Debounce keeps us from spamming the backend on every
// keystroke.
const SEARCH_DEBOUNCE_MS = 300;
const SEARCH_PAGE_SIZE = 250;

export default function NewsList({ articles: initialArticles, totalCount: initialTotal }: Props) {
  const t = useTranslations("news");
  const [activeTab, setActiveTab] = useState<Category>("all");
  const [searchInput, setSearchInput] = useState("");
  const [searchedArticles, setSearchedArticles] = useState<NewsArticle[] | null>(null);
  const [searchedTotal, setSearchedTotal] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);

  // Debounced live API search — empty query reverts to initial articles.
  useEffect(() => {
    const trimmed = searchInput.trim();
    if (!trimmed) {
      setSearchedArticles(null);
      setSearchedTotal(null);
      setSearching(false);
      return;
    }
    setSearching(true);
    let cancelled = false;
    const handle = setTimeout(async () => {
      try {
        const data = await fetchNews({
          search: trimmed,
          pageSize: SEARCH_PAGE_SIZE,
        });
        if (cancelled) return;
        setSearchedArticles(data.results);
        setSearchedTotal(data.count);
      } catch {
        if (cancelled) return;
        setSearchedArticles([]);
        setSearchedTotal(0);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [searchInput]);

  const activeArticles = searchedArticles ?? initialArticles;
  const activeTotal = searchedTotal ?? initialTotal;

  const filtered = useMemo(() => {
    return activeArticles.filter((article) => {
      if (activeTab === "school" && article.mentioned_schools.length === 0) return false;
      if (activeTab === "general" && article.mentioned_schools.length > 0) return false;
      return true;
    });
  }, [activeArticles, activeTab]);

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
    setSearchInput(value);
    setCurrentPage(1);
  };
  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  // Compute most mentioned schools (always over the initial 250 — the
  // sidebar shouldn't shuffle to follow what the user is searching for).
  const topSchools = useMemo(() => {
    const schoolCounts = new Map<string, { name: string; moe_code: string; count: number }>();
    initialArticles.forEach((article) => {
      article.mentioned_schools.forEach((school) => {
        if (!school.moe_code) return;
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
  }, [initialArticles]);

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

          <div className="flex-1 min-w-[200px] relative">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            {searching && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">
                {t.has("searching") ? t("searching") : "Searching..."}
              </span>
            )}
          </div>
        </div>

        {/* Article list */}
        {paged.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-sm">
              {searchInput.trim() ? t("noArticlesFiltered") : t("noArticles")}
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
          <PaginationBar
            currentPage={safePage}
            totalPages={totalPages}
            totalItems={filtered.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={handlePageSizeChange}
            showingLabel={(from, to, total) => t("showingCount", { from, to, total })}
          />
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
                    href={schoolPath({moe_code: school.moe_code, short_name: school.name})}
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
