"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";

export default function ProfilePage() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

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
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {profile.display_name}
            </h1>
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

        {/* Claim school CTA if no admin school */}
        {!profile.admin_school && (
          <div className="border border-gray-200 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600 mb-2">
              {t("claimSchoolCta")}
            </p>
            <Link
              href="/claim"
              className="inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              {t("claimSchool")} &rarr;
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
