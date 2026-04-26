"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";
import { fetchSchoolDetail } from "@/lib/api";
import ImageManager from "@/components/ImageManager";

/**
 * School-image manager. Always operates on a single school identified by
 * the `?school=<moe>` query parameter, which is set by the "Manage images"
 * link on the school edit page. Bound school admins are auto-redirected
 * to their own school. SUPERADMIN must arrive with the param set.
 */
export default function DashboardImagesPage() {
  const t = useTranslations("suggestions");
  const { status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const searchParams = useSearchParams();
  const moeFromQuery = searchParams.get("school") || "";
  const [moeCode, setMoeCode] = useState(moeFromQuery);
  const [schoolName, setSchoolName] = useState<string>("");

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  // Bound school admin without query param → use their school.
  useEffect(() => {
    if (!profile) return;
    if (!moeFromQuery && profile.role !== "SUPERADMIN" && profile.admin_school) {
      setMoeCode(profile.admin_school.moe_code);
      setSchoolName(profile.admin_school.name);
    }
  }, [profile, moeFromQuery]);

  // Resolve a friendly school name once we know the moe code.
  useEffect(() => {
    if (!moeCode) return;
    if (schoolName) return;
    fetchSchoolDetail(moeCode)
      .then((s) => setSchoolName(s.short_name || s.name))
      .catch(() => setSchoolName(moeCode));
  }, [moeCode, schoolName]);

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

  const canManage =
    profile.role === "SUPERADMIN" ||
    Boolean(profile.admin_school && profile.admin_school.moe_code === moeCode);

  if (!moeCode) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500 space-y-3">
        <p>Open this page from a school&rsquo;s edit page.</p>
        <p className="text-xs text-gray-400">
          The image manager always operates on a specific school. Use the
          &ldquo;Manage images&rdquo; button on the school&rsquo;s edit page.
        </p>
      </div>
    );
  }

  if (!canManage) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        {t("notSchoolAdmin")}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            {t("imageManager")}
          </h1>
          <p className="text-sm text-gray-500">
            {schoolName || moeCode}
          </p>
        </div>
        <Link
          href={`/school/${moeCode}/edit`}
          className="text-sm text-primary-600 hover:underline whitespace-nowrap"
        >
          ← Back to edit
        </Link>
      </div>
      <ImageManager moeCode={moeCode} />
    </div>
  );
}
