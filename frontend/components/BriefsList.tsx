"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { SittingBrief } from "@/lib/types";
import PaginationBar from "./PaginationBar";

const CARDS_PER_PAGE = 10;

/**
 * Extract a blurb from the brief HTML — content before the first heading,
 * truncated to ~150 chars at a word boundary.
 */
function extractBlurb(html: string): string {
  // Get content before the first heading (h2 or h3)
  const match = html.match(/^([\s\S]*?)(?=<h[23]>)/i);
  if (match && match[1].trim()) {
    const plain = match[1].replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    if (plain.length > 0) {
      if (plain.length <= 150) return plain;
      return plain.slice(0, 150).replace(/\s+\S*$/, "") + "...";
    }
  }
  // Fallback: strip all tags and take first 150 chars
  const plain = html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  if (plain.length <= 150) return plain;
  return plain.slice(0, 150).replace(/\s+\S*$/, "") + "...";
}

interface BriefsListProps {
  briefs: SittingBrief[];
}

export default function BriefsList({ briefs }: BriefsListProps) {
  const t = useTranslations("parliamentWatch");
  const [pageSize, setPageSize] = useState(CARDS_PER_PAGE);
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(briefs.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paged = briefs.slice(startIndex, startIndex + pageSize);

  return (
    <div className="mb-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {paged.map((brief) => {
          const blurb = extractBlurb(brief.summary_html);
          const headline = brief.title.replace(/\s*[—–-]\s*\d{1,2}\s+\w+\s+\d{4}$/, "");

          return (
            <Link
              key={brief.id}
              href={`/parliament-watch/sittings/${brief.id}`}
              className="group block bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all p-5"
            >
              <p className="text-xs text-gray-400 mb-1.5">
                {new Date(brief.sitting_date).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </p>
              <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary-700 transition-colors mb-2 line-clamp-2">
                {headline}
              </h3>
              <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                {blurb}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {brief.mention_count}{" "}
                  {brief.mention_count === 1 ? "mention" : "mentions"}
                </span>
                <span className="text-sm font-medium text-primary-600 group-hover:text-primary-700">
                  {t("readFullReport")} &rarr;
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {briefs.length > CARDS_PER_PAGE && (
        <div className="mt-6">
          <PaginationBar
            currentPage={safePage}
            totalPages={totalPages}
            totalItems={briefs.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
            showingLabel={(from, to, total) =>
              t("showingCount", { from, to, total })
            }
          />
        </div>
      )}
    </div>
  );
}
