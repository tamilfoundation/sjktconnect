"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { NewsArticle } from "@/lib/types";

interface Props {
  articles: NewsArticle[];
}

function sentimentColour(sentiment: string): string {
  switch (sentiment) {
    case "POSITIVE":
      return "bg-green-100 text-green-800";
    case "NEGATIVE":
      return "bg-red-100 text-red-800";
    case "MIXED":
      return "bg-yellow-100 text-yellow-800";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function NewsWatchSection({ articles }: Props) {
  const t = useTranslations("parliamentWatch");

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">{t("newsWatchHeading")}</h2>

      {articles.length === 0 ? (
        <>
          <p className="text-sm text-gray-500 mb-3">
            {t("noNewsSubscribe")}
          </p>
          <Link
            href="/subscribe"
            className="inline-block text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            {t("subscribeCta")} →
          </Link>
        </>
      ) : (
        <ul className="space-y-4">
          {articles.map((article) => (
            <li
              key={article.id}
              className="border-b border-gray-100 pb-4 last:border-0 last:pb-0"
            >
              <div className="flex items-start justify-between gap-2">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-blue-700 hover:underline"
                >
                  {article.title}
                </a>
                {article.is_urgent && (
                  <span className="shrink-0 text-xs bg-red-600 text-white px-2 py-0.5 rounded-full">
                    {t("urgent")}
                  </span>
                )}
              </div>

              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                <span>{article.source_name}</span>
                {article.published_date && (
                  <>
                    <span>&middot;</span>
                    <span>{formatDate(article.published_date)}</span>
                  </>
                )}
                <span
                  className={`px-1.5 py-0.5 rounded text-xs font-medium ${sentimentColour(article.sentiment)}`}
                >
                  {article.sentiment.charAt(0) + article.sentiment.slice(1).toLowerCase()}
                </span>
              </div>

              {article.ai_summary && (
                <p className="mt-1 text-sm text-gray-600">{article.ai_summary}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
