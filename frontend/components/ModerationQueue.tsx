"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  fetchPendingSuggestions,
  approveSuggestion,
  rejectSuggestion,
} from "@/lib/api";
import { Suggestion } from "@/lib/types";

export default function ModerationQueue() {
  const t = useTranslations("suggestions");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchPendingSuggestions()
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: number) => {
    setActionLoading(id);
    try {
      await approveSuggestion(id);
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
    } catch {
      // silently fail
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: number) => {
    if (!rejectReason.trim()) return;
    setActionLoading(id);
    try {
      await rejectSuggestion(id, rejectReason.trim());
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
      setRejectingId(null);
      setRejectReason("");
    } catch {
      // silently fail
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="text-center text-gray-500 py-8">Loading...</div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
        <p className="text-sm text-gray-500">{t("noPending")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {suggestions.map((s) => (
        <div
          key={s.id}
          className="bg-white rounded-xl border border-gray-200 p-5"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                {s.school_name}
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {t("submittedBy")} {s.user_name} &middot;{" "}
                {new Date(s.created_at).toLocaleDateString()}
              </p>
            </div>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800">
              {t(s.type === "DATA_CORRECTION" ? "dataCorrection" : s.type === "PHOTO_UPLOAD" ? "photoUpload" : "note")}
            </span>
          </div>

          {/* Data correction: current vs suggested */}
          {s.type === "DATA_CORRECTION" && (
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div className="bg-red-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">
                  {t("currentValue")} ({s.field_name})
                </p>
                <p className="text-sm text-gray-900">
                  {s.current_value || "—"}
                </p>
              </div>
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">
                  {t("suggestedValue")}
                </p>
                <p className="text-sm text-gray-900">
                  {s.suggested_value || "—"}
                </p>
              </div>
            </div>
          )}

          {/* Photo upload: image preview */}
          {s.type === "PHOTO_UPLOAD" && s.suggested_value && (
            <div className="mb-3">
              <img
                src={s.suggested_value}
                alt="Suggested photo"
                className="max-h-48 rounded-lg object-cover"
              />
            </div>
          )}

          {/* Note */}
          {s.note && (
            <p className="text-sm text-gray-600 mb-3">{s.note}</p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleApprove(s.id)}
              disabled={actionLoading === s.id}
              className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50"
            >
              {t("approve")}
            </button>
            {rejectingId === s.id ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="text"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder={t("rejectionReason")}
                  className="flex-1 text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-red-500"
                />
                <button
                  onClick={() => handleReject(s.id)}
                  disabled={actionLoading === s.id || !rejectReason.trim()}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
                >
                  {t("reject")}
                </button>
                <button
                  onClick={() => {
                    setRejectingId(null);
                    setRejectReason("");
                  }}
                  className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700"
                >
                  &times;
                </button>
              </div>
            ) : (
              <button
                onClick={() => setRejectingId(s.id)}
                className="px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50 rounded-lg"
              >
                {t("reject")}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
