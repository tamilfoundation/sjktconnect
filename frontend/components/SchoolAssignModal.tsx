"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { AdminUserRow, updateAdminUser, searchEntities } from "@/lib/api";

interface SchoolAssignModalProps {
  user: AdminUserRow;
  onClose: () => void;
  onSaved: (updated: AdminUserRow) => void;
}

interface SchoolHit {
  moe_code: string;
  name: string;
  state?: string;
}

export default function SchoolAssignModal({ user, onClose, onSaved }: SchoolAssignModalProps) {
  const t = useTranslations("userManagement");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SchoolHit[]>([]);
  const [selected, setSelected] = useState<string | null>(user.admin_school?.moe_code ?? null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    let cancelled = false;
    searchEntities(query.trim()).then((r) => {
      if (!cancelled) setHits(r.schools.slice(0, 10) as unknown as SchoolHit[]);
    }).catch(() => { if (!cancelled) setHits([]); });
    return () => { cancelled = true; };
  }, [query]);

  const submit = async (assign: string | null) => {
    setSaving(true);
    setError("");
    try {
      const updated = await updateAdminUser(user.id, { admin_school: assign });
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">
            {t("assignSchoolTitle", { name: user.display_name })}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-3 text-sm">
          {user.admin_school && (
            <div className="p-3 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">{t("currentAssignment")}</p>
                <p className="font-medium">{user.admin_school.name} ({user.admin_school.moe_code})</p>
              </div>
              <button
                onClick={() => submit(null)}
                disabled={saving}
                className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded border border-red-200"
              >
                {t("unassign")}
              </button>
            </div>
          )}

          <div>
            <label className="block text-xs text-gray-500 mb-1">{t("searchSchool")}</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              autoFocus
            />
          </div>

          {hits.length > 0 && (
            <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-64 overflow-y-auto">
              {hits.map((h) => (
                <li
                  key={h.moe_code}
                  onClick={() => setSelected(h.moe_code)}
                  className={`p-3 text-sm cursor-pointer hover:bg-gray-50 ${
                    selected === h.moe_code ? "bg-primary-50" : ""
                  }`}
                >
                  <p className="font-medium">{h.name}</p>
                  <p className="text-xs text-gray-500">{h.moe_code}{h.state ? ` · ${h.state}` : ""}</p>
                </li>
              ))}
            </ul>
          )}

          {error && <p className="text-sm text-red-600 pt-2">{error}</p>}

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-100">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg"
            >
              {t("cancel")}
            </button>
            <button
              onClick={() => selected && submit(selected)}
              disabled={saving || !selected || selected === user.admin_school?.moe_code}
              className="px-4 py-2 text-sm bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? t("saving") : t("assign")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
