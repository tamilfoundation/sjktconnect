"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";
import ImageManager from "@/components/ImageManager";

export default function DashboardImagesPage() {
  const t = useTranslations("suggestions");
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
        Please sign in to access this page.
      </div>
    );
  }

  if (!profile.admin_school) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        {t("notSchoolAdmin")}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {t("imageManager")}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {profile.admin_school.name}
      </p>
      <ImageManager moeCode={profile.admin_school.moe_code} />
    </div>
  );
}
