"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  AdminUserRow,
  fetchAdminUsers,
  fetchMe,
} from "@/lib/api";
import UserManagementTable from "@/components/UserManagementTable";

export default function UsersDashboardPage() {
  const t = useTranslations("userManagement");
  const router = useRouter();

  const [currentProfileId, setCurrentProfileId] = useState<number | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [role, setRole] = useState("");
  const [hasAdminSchool, setHasAdminSchool] = useState("");
  const [isActive, setIsActive] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchAdminUsers({
        role: role || undefined,
        has_admin_school: (hasAdminSchool || undefined) as "true" | "false" | undefined,
        is_active: (isActive || undefined) as "true" | "false" | undefined,
        search: search || undefined,
      });
      setUsers(data.results);
      setCount(data.count);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [role, hasAdminSchool, isActive, search]);

  // Gate by SUPERADMIN on mount. Uses .catch so a 401 from the backend
  // (signed-out user with no Django session) doesn't fall through to the
  // page chrome — TD-16. Render-side `currentProfileId === null` keeps the
  // table hidden until auth resolves.
  useEffect(() => {
    fetchMe()
      .then((me) => {
        if (!me) {
          router.push("/");
          return;
        }
        if (me.role !== "SUPERADMIN") {
          router.push("/dashboard");
          return;
        }
        setCurrentProfileId(me.id);
        load();
      })
      .catch(() => router.push("/"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-load on filter change (after initial auth-check loaded)
  useEffect(() => {
    if (currentProfileId !== null) load();
  }, [role, hasAdminSchool, isActive, search, currentProfileId, load]);

  const onChange = (updated: AdminUserRow) => {
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
  };

  if (currentProfileId === null) {
    return <div className="p-8 text-gray-500 text-sm">{t("loading")}</div>;
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="text-sm text-gray-500 mt-1">{t("description", { count })}</p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">{t("filterRole")}</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">{t("allRoles")}</option>
              <option value="SUPERADMIN">{t("role_SUPERADMIN")}</option>
              <option value="MODERATOR">{t("role_MODERATOR")}</option>
              <option value="USER">{t("role_USER")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{t("filterSchoolAdmin")}</label>
            <select
              value={hasAdminSchool}
              onChange={(e) => setHasAdminSchool(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">{t("any")}</option>
              <option value="true">{t("hasAdminSchool")}</option>
              <option value="false">{t("noAdminSchool")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{t("filterStatus")}</label>
            <select
              value={isActive}
              onChange={(e) => setIsActive(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">{t("any")}</option>
              <option value="true">{t("active")}</option>
              <option value="false">{t("inactive")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">{t("filterSearch")}</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("searchPlaceholderMain")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500">{t("loading")}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <UserManagementTable
          users={users}
          currentProfileId={currentProfileId}
          onChange={onChange}
        />
      )}
    </div>
  );
}
