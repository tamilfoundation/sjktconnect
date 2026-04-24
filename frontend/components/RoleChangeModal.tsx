"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AdminUserRow, updateAdminUser } from "@/lib/api";

interface RoleChangeModalProps {
  user: AdminUserRow;
  onClose: () => void;
  onSaved: (updated: AdminUserRow) => void;
}

const ROLES: Array<AdminUserRow["role"]> = ["SUPERADMIN", "MODERATOR", "USER"];

export default function RoleChangeModal({ user, onClose, onSaved }: RoleChangeModalProps) {
  const t = useTranslations("userManagement");
  const [role, setRole] = useState<AdminUserRow["role"]>(user.role);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (role === user.role) {
      onClose();
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await updateAdminUser(user.id, { role });
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
            {t("changeRoleTitle", { name: user.display_name })}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-3 text-sm">
          {ROLES.map((r) => (
            <label
              key={r}
              className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                role === r ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              <input
                type="radio"
                name="role"
                value={r}
                checked={role === r}
                onChange={() => setRole(r)}
                className="text-primary-600"
              />
              <span className="font-medium text-gray-700">{t(`role_${r}`)}</span>
            </label>
          ))}

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
              onClick={submit}
              disabled={saving}
              className="px-4 py-2 text-sm bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? t("saving") : t("save")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
