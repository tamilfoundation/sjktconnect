"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { NewsArticle } from "@/lib/types";
import NewsCard from "./NewsCard";

interface Props {
  articles: NewsArticle[];
  totalCount: number;
}

type Category = "all" | "school" | "general";

export default function NewsList({ articles, totalCount }: Props) {
  const t = useTranslations("news");
  const [activeTab, setActiveTab] = useState<Category>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = articles.filter((article) => {
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

  // Compute most mentioned schools
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
  const topSchools = Array.from(schoolCounts.values())
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

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
                onClick={() => setActiveTab(tab.key)}
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
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 min-w-[200px] focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Article list */}
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-sm">
              {searchQuery ? t("noArticlesFiltered") : t("noArticles")}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((article) => (
              <NewsCard key={article.id} article={article} />
            ))}
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
