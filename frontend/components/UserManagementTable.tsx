"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AdminUserRow, deactivateAdminUser, updateAdminUser } from "@/lib/api";
import RoleChangeModal from "@/components/RoleChangeModal";
import SchoolAssignModal from "@/components/SchoolAssignModal";

interface UserManagementTableProps {
  users: AdminUserRow[];
  currentProfileId: number;
  onChange: (updated: AdminUserRow) => void;
}

export default function UserManagementTable({
  users,
  currentProfileId,
  onChange,
}: UserManagementTableProps) {
  const t = useTranslations("userManagement");
  const [roleEditing, setRoleEditing] = useState<AdminUserRow | null>(null);
  const [schoolEditing, setSchoolEditing] = useState<AdminUserRow | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  const toggleActive = async (u: AdminUserRow) => {
    if (u.id === currentProfileId) return;
    setPending(u.id);
    try {
      if (u.is_active) {
        await deactivateAdminUser(u.id);
        onChange({ ...u, is_active: false });
      } else {
        const updated = await updateAdminUser(u.id, { is_active: true });
        onChange(updated);
      }
    } finally {
      setPending(null);
    }
  };

  return (
    <>
      <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">{t("user")}</th>
              <th className="text-left px-4 py-3">{t("email")}</th>
              <th className="text-left px-4 py-3">{t("role")}</th>
              <th className="text-left px-4 py-3">{t("adminSchool")}</th>
              <th className="text-left px-4 py-3">{t("points")}</th>
              <th className="text-left px-4 py-3">{t("status")}</th>
              <th className="text-right px-4 py-3">{t("actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  {t("noUsers")}
                </td>
              </tr>
            )}
            {users.map((u) => {
              const isSelf = u.id === currentProfileId;
              return (
                <tr key={u.id} className={isSelf ? "bg-primary-50/30" : ""}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {u.avatar_url ? (
                        <img
                          src={u.avatar_url}
                          alt=""
                          className="w-8 h-8 rounded-full"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600">
                          {u.display_name.charAt(0).toUpperCase() || "?"}
                        </div>
                      )}
                      <div>
                        <p className="font-medium text-gray-900">{u.display_name}</p>
                        {isSelf && <p className="text-xs text-primary-600">{t("you")}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      u.role === "SUPERADMIN" ? "bg-purple-100 text-purple-800"
                        : u.role === "MODERATOR" ? "bg-blue-100 text-blue-800"
                        : "bg-gray-100 text-gray-700"
                    }`}>
                      {t(`role_${u.role}`)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700 text-xs">
                    {u.admin_school ? (
                      <span>{u.admin_school.moe_code} · {u.admin_school.name}</span>
                    ) : (
                      <span className="text-gray-400">{t("none")}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{u.points}</td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-700">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        {t("active")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <span className="w-2 h-2 rounded-full bg-gray-400"></span>
                        {t("inactive")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-2">
                      <button
                        onClick={() => setRoleEditing(u)}
                        disabled={isSelf}
                        title={isSelf ? t("cannotEditSelfRole") : t("changeRole")}
                        className="px-2 py-1 text-xs text-gray-700 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {t("changeRole")}
                      </button>
                      <button
                        onClick={() => setSchoolEditing(u)}
                        className="px-2 py-1 text-xs text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
                      >
                        {t("school")}
                      </button>
                      <button
                        onClick={() => toggleActive(u)}
                        disabled={isSelf || pending === u.id}
                        title={isSelf ? t("cannotDeactivateSelf") : ""}
                        className={`px-2 py-1 text-xs border rounded disabled:opacity-40 disabled:cursor-not-allowed ${
                          u.is_active
                            ? "text-red-700 border-red-200 hover:bg-red-50"
                            : "text-green-700 border-green-200 hover:bg-green-50"
                        }`}
                      >
                        {u.is_active ? t("deactivate") : t("reactivate")}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {roleEditing && (
        <RoleChangeModal
          user={roleEditing}
          onClose={() => setRoleEditing(null)}
          onSaved={onChange}
        />
      )}
      {schoolEditing && (
        <SchoolAssignModal
          user={schoolEditing}
          onClose={() => setSchoolEditing(null)}
          onSaved={onChange}
        />
      )}
    </>
  );
}
