"use client";

import { useTranslations } from "next-intl";
import { ConstituencyMention, Scorecard } from "@/lib/types";

interface ScorecardCardProps {
  scorecard: Scorecard | null;
  mpName: string;
  mentions?: ConstituencyMention[];
}

export default function ScorecardCard({
  scorecard,
  mpName,
  mentions = [],
}: ScorecardCardProps) {
  const t = useTranslations("constituency");
  if (!scorecard) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("scorecardTitle")}
        </h2>
        <p className="text-sm text-gray-500">
          {t("noActivity", { name: mpName })}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        {t("scorecardTitle")}
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.total_mentions}
          </div>
          <div className="text-xs text-gray-500 mt-1">{t("totalMentions")}</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.substantive_mentions}
          </div>
          <div className="text-xs text-gray-500 mt-1">{t("substantive")}</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.questions_asked}
          </div>
          <div className="text-xs text-gray-500 mt-1">{t("questionsAsked")}</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-700">
            {scorecard.commitments_made}
          </div>
          <div className="text-xs text-gray-500 mt-1">{t("commitments")}</div>
        </div>
      </div>
      {scorecard.last_mention_date && (
        <p className="text-xs text-gray-400 mt-4 text-center">
          {t("lastMention")}{" "}
          {new Date(scorecard.last_mention_date).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      )}

      {/* Recent mentions */}
      {mentions.length > 0 && (
        <div className="mt-5 pt-5 border-t border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            {t("recentMentions")}
          </h3>
          <div className="space-y-3">
            {mentions.slice(0, 5).map((mention, index) => (
              <div
                key={index}
                className="border-l-3 border-primary-300 pl-3 py-1"
              >
                <p className="text-sm text-gray-700 line-clamp-2">
                  {mention.ai_summary}
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <span className="text-xs text-gray-400">
                    {new Date(mention.sitting_date).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                  {mention.mention_type && (
                    <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                      {mention.mention_type}
                    </span>
                  )}
                  {mention.significance && mention.significance >= 4 && (
                    <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                      {mention.significance}/5
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
