"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { NewsArticle } from "@/lib/types";

interface Props {
  article: NewsArticle;
}

function sentimentColour(sentiment: string): string {
  switch (sentiment) {
    case "POSITIVE": return "bg-green-100 text-green-800";
    case "NEGATIVE": return "bg-red-100 text-red-800";
    case "MIXED": return "bg-yellow-100 text-yellow-800";
    default: return "bg-gray-100 text-gray-700";
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

/** Strip trailing source name from title (e.g. " - bernama", " - The Star | Malaysia") */
function cleanTitle(title: string, sourceName: string): string {
  // Remove " - Source" or " - Source | Extra" from end of title
  const patterns = [
    ` - ${sourceName}`,
    ` | ${sourceName}`,
  ];
  let cleaned = title;
  for (const p of patterns) {
    if (cleaned.toLowerCase().endsWith(p.toLowerCase())) {
      cleaned = cleaned.slice(0, -p.length);
      break;
    }
  }
  // Also strip trailing " | Country" or " - Source | Country" patterns
  cleaned = cleaned.replace(/\s*[-|]\s*[A-Z][a-z]+(\s*\|\s*[A-Z][a-z]+)*\s*$/, "");
  return cleaned || title;
}

export default function NewsCard({ article }: Props) {
  const t = useTranslations("news");
  const displayTitle = cleanTitle(article.title, article.source_name);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <a href={article.url} target="_blank" rel="noopener noreferrer"
           className="text-base font-medium text-blue-700 hover:underline leading-snug">
          {displayTitle}
        </a>
        {article.is_urgent && (
          <span className="shrink-0 text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-medium">
            {t("urgent")}
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
        <span>{article.source_name}</span>
        {article.published_date && (
          <>
            <span>&middot;</span>
            <span>{formatDate(article.published_date)}</span>
          </>
        )}
        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${sentimentColour(article.sentiment)}`}>
          {article.sentiment.charAt(0) + article.sentiment.slice(1).toLowerCase()}
        </span>
      </div>

      {article.ai_summary && (
        <p className="mt-2 text-sm text-gray-600 leading-relaxed">{article.ai_summary}</p>
      )}

      {article.mentioned_schools.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {article.mentioned_schools.map((school, idx) =>
            school.moe_code ? (
              <Link key={school.moe_code} href={`/school/${school.moe_code}`}
                    className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full hover:bg-primary-100">
                {school.name}
              </Link>
            ) : (
              <span key={`${school.name}-${idx}`}
                    className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {school.name}
              </span>
            )
          )}
        </div>
      )}
    </div>
  );
}
