"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";
import { updateMyProfile } from "@/lib/api";
import MySuggestions from "@/components/MySuggestions";

export default function ProfilePage() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState("");

  useEffect(() => {
    fetchProfile()
      .then((p) => {
        setProfile(p);
        if (p) setNameDraft(p.display_name);
      })
      .finally(() => setLoading(false));
  }, []);

  const saveName = async () => {
    if (!profile) return;
    const trimmed = nameDraft.trim();
    if (trimmed.length < 1) {
      setNameError(t("nameEmpty"));
      return;
    }
    setSavingName(true);
    setNameError("");
    try {
      const updated = await updateMyProfile(trimmed);
      setProfile({ ...profile, display_name: updated.display_name });
      setEditingName(false);
    } catch (err) {
      setNameError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSavingName(false);
    }
  };

  if (status === "loading" || loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (!session || !profile) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-600 mb-4">{t("signInRequired")}</p>
      </div>
    );
  }

  const roleBadgeColor = {
    SUPERADMIN: "bg-red-100 text-red-800",
    MODERATOR: "bg-purple-100 text-purple-800",
    USER: "bg-blue-100 text-blue-800",
  }[profile.role];

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {/* Avatar + Name */}
        <div className="flex items-center gap-4 mb-6">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt=""
              className="w-16 h-16 rounded-full border-2 border-gray-200"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center text-2xl font-bold text-primary-700">
              {profile.display_name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1">
            {editingName ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={nameDraft}
                  onChange={(e) => setNameDraft(e.target.value)}
                  maxLength={200}
                  className="flex-1 text-xl font-bold text-gray-900 border border-gray-300 rounded px-2 py-1"
                  autoFocus
                />
                <button
                  onClick={saveName}
                  disabled={savingName}
                  className="px-3 py-1 text-sm bg-primary-600 text-white rounded disabled:opacity-50"
                >
                  {savingName ? t("saving") : t("save")}
                </button>
                <button
                  onClick={() => {
                    setEditingName(false);
                    setNameDraft(profile.display_name);
                    setNameError("");
                  }}
                  className="px-3 py-1 text-sm text-gray-700 border border-gray-300 rounded"
                >
                  {t("cancel")}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-gray-900">
                  {profile.display_name}
                </h1>
                <button
                  onClick={() => setEditingName(true)}
                  className="text-xs text-blue-600 hover:text-blue-800 underline"
                  aria-label={t("editDisplayName")}
                >
                  {t("edit")}
                </button>
              </div>
            )}
            {nameError && <p className="text-xs text-red-600 mt-1">{nameError}</p>}
            <p className="text-sm text-gray-500">{profile.email}</p>
            <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${roleBadgeColor}`}>
              {t(`role_${profile.role}`)}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">{profile.points}</p>
            <p className="text-xs text-gray-500">{t("points")}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">
              {profile.admin_school ? "1" : "0"}
            </p>
            <p className="text-xs text-gray-500">{t("schoolsManaged")}</p>
          </div>
        </div>

        {/* Admin School */}
        {profile.admin_school && (
          <div className="border border-primary-100 bg-primary-50 rounded-lg p-4 mb-6">
            <p className="text-xs text-primary-600 font-medium mb-1">
              {t("yourSchool")}
            </p>
            <Link
              href={`/school/${profile.admin_school.moe_code}`}
              className="text-base font-semibold text-primary-900 hover:text-primary-700"
            >
              {profile.admin_school.name}
            </Link>
          </div>
        )}

        {/* Hint for non-admin users: sign in with @moe.edu.my to auto-claim */}
        {!profile.admin_school && (
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">
              {t("noSchoolHint")}
            </p>
          </div>
        )}
      </div>

      {/* My Suggestions */}
      <div className="mt-6">
        <MySuggestions />
      </div>
    </div>
  );
}
