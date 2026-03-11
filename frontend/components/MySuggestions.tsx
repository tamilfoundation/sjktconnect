"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMySuggestions } from "@/lib/api";
import { Suggestion } from "@/lib/types";

const statusBadge: Record<string, string> = {
  APPROVED: "bg-green-100 text-green-800",
  PENDING: "bg-yellow-100 text-yellow-800",
  REJECTED: "bg-red-100 text-red-800",
};

const typeLabels: Record<string, string> = {
  DATA_CORRECTION: "dataCorrection",
  PHOTO_UPLOAD: "photoUpload",
  NOTE: "note",
};

export default function MySuggestions() {
  const t = useTranslations("suggestions");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMySuggestions()
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="text-center text-gray-500 py-4">Loading...</div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          {t("mySuggestions")}
        </h2>
        <p className="text-sm text-gray-500">{t("noSuggestions")}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        {t("mySuggestions")}
      </h2>
      <div className="space-y-3">
        {suggestions.map((s) => (
          <div
            key={s.id}
            className="border border-gray-100 rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900">
                {s.school_name}
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge[s.status]}`}
              >
                {t(s.status.toLowerCase() as "approved" | "pending" | "rejected")}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{t(typeLabels[s.type] || "note")}</span>
              <span>&middot;</span>
              <span>
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            </div>
            {s.status === "APPROVED" && s.points_awarded > 0 && (
              <p className="text-xs text-green-700 mt-1">
                +{s.points_awarded} {t("pointsAwarded")}
              </p>
            )}
            {s.status === "REJECTED" && s.review_note && (
              <p className="text-xs text-red-600 mt-1">
                {s.review_note}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
