"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  approvePhotoSuggestion,
  approveSuggestion,
  fetchPendingSuggestions,
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
  const [slotFullSchools, setSlotFullSchools] = useState<Set<string>>(new Set());
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingSuggestions()
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (s: Suggestion) => {
    setActionLoading(s.id);
    setActionError(null);
    try {
      if (s.type === "PHOTO_UPLOAD") {
        const result = await approvePhotoSuggestion(s.id);
        if (!result.ok) {
          if (result.slot_full) {
            setSlotFullSchools((prev) => new Set(prev).add(s.school_moe_code));
            setActionError(
              result.detail ||
                `Photo slot full for ${s.school_name}. Delete an existing photo first.`,
            );
          } else {
            setActionError(result.detail || "Failed to approve.");
          }
          return;
        }
      } else {
        await approveSuggestion(s.id);
      }
      setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
    } catch {
      setActionError("Failed to approve.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: number) => {
    if (!rejectReason.trim()) return;
    setActionLoading(id);
    setActionError(null);
    try {
      await rejectSuggestion(id, rejectReason.trim());
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
      setRejectingId(null);
      setRejectReason("");
    } catch {
      setActionError("Failed to reject.");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return <div className="text-center text-gray-500 py-8">Loading...</div>;
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
      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {actionError}
        </div>
      )}
      {suggestions.map((s) => {
        const slotFull = slotFullSchools.has(s.school_moe_code);
        return (
          <div
            key={s.id}
            className="bg-white rounded-xl border border-gray-200 p-5"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">
                  {s.school_moe_code ? (
                    <Link
                      href={`/school/${s.school_moe_code}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-700 hover:underline"
                    >
                      {s.school_name}
                    </Link>
                  ) : (
                    s.school_name
                  )}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t("submittedBy")} {s.user_name} &middot;{" "}
                  {new Date(s.created_at).toLocaleDateString()}
                </p>
              </div>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800">
                {t(
                  s.type === "DATA_CORRECTION"
                    ? "dataCorrection"
                    : s.type === "PHOTO_UPLOAD"
                    ? "photoUpload"
                    : "note",
                )}
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

            {/* Photo upload: image preview from pending_image_url (Sprint 14) */}
            {s.type === "PHOTO_UPLOAD" && s.pending_image_url && (
              <div className="mb-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={s.pending_image_url}
                  alt="Pending photo"
                  className="max-h-64 rounded-lg object-cover border border-gray-200"
                />
              </div>
            )}

            {/* Note / caption */}
            {s.note && (
              <p className="text-sm text-gray-600 mb-3 whitespace-pre-wrap">
                {s.note}
              </p>
            )}

            {slotFull && (
              <p className="mb-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                This school is at the 20-photo limit. Delete an existing photo
                in the school&rsquo;s image manager before approving any new
                uploads.
              </p>
            )}

            {/* Actions */}
            <div className="flex items-start gap-2 flex-wrap">
              <button
                onClick={() => handleApprove(s)}
                disabled={actionLoading === s.id}
                className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50"
              >
                {t("approve")}
              </button>
              {rejectingId === s.id ? (
                <div className="flex flex-col gap-2 flex-1 min-w-0">
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    rows={2}
                    placeholder={t("rejectionReason")}
                    className="w-full text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-red-500"
                  />
                  <div className="flex gap-2">
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
                      Cancel
                    </button>
                  </div>
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
        );
      })}
    </div>
  );
}
