"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";
import { Link } from "@/i18n/navigation";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  if (status === "loading" || loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        Please sign in to access the dashboard.
      </div>
    );
  }

  const isSuperAdmin = profile.role === "SUPERADMIN";
  const isModerator = profile.role === "MODERATOR" || isSuperAdmin;
  const isSchoolAdmin = !!profile.admin_school;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {t("heading")}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {t("welcome", { name: profile.display_name })}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* School Admin section */}
        {isSchoolAdmin && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("mySchool")}
            </h2>
            <p className="text-sm text-gray-600 mb-3">
              {profile.admin_school!.name}
            </p>
            <p className="text-xs text-gray-400">{t("comingSoon")}</p>
          </div>
        )}

        {/* Moderation section */}
        {(isModerator || isSchoolAdmin) && (
          <Link
            href="/dashboard/suggestions"
            className="bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all block"
          >
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("moderation")}
            </h2>
            <p className="text-xs text-gray-500">
              Review and approve community suggestions.
            </p>
          </Link>
        )}

        {/* Super Admin section */}
        {isSuperAdmin && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("administration")}
            </h2>
            <p className="text-xs text-gray-400">{t("comingSoon")}</p>
          </div>
        )}

        {/* All users: contributions */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-2">
            {t("myContributions")}
          </h2>
          <p className="text-xs text-gray-400">{t("comingSoon")}</p>
        </div>
      </div>
    </div>
  );
}
