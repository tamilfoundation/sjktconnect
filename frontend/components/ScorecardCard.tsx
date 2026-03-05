"use client";

import { useTranslations } from "next-intl";
import { Scorecard } from "@/lib/types";

interface ScorecardCardProps {
  scorecard: Scorecard | null;
  mpName: string;
}

export default function ScorecardCard({
  scorecard,
  mpName,
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
    </div>
  );
}
