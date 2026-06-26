"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { fetchSchoolEdit, fetchMe } from "@/lib/api";
import { SchoolEditData } from "@/lib/types";
import { parseSchoolSlug, schoolPath } from "@/lib/urls";
import Breadcrumb from "@/components/Breadcrumb";
import SchoolEditForm from "@/components/SchoolEditForm";

export default function SchoolEditPage() {
  const params = useParams();
  const router = useRouter();
  // Sprint 28 — `params.moe_code` is now a SLUG, not a bare moe_code.
  // Resolve to the canonical moe_code via parseSchoolSlug.
  const rawSegment = params.moe_code as string;
  const moeCode = parseSchoolSlug(rawSegment) ?? "";
  const t = useTranslations("schoolEdit");
  const tc = useTranslations("common");

  const [school, setSchool] = useState<SchoolEditData | null>(null);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      // Check authentication first
      const user = await fetchMe();
      if (!user) {
        router.push("/sign-in");
        return;
      }
      const superadmin = user.role === "SUPERADMIN";
      const isSchoolAdmin = user.admin_school?.moe_code === moeCode;
      if (!superadmin && !isSchoolAdmin) {
        setError(t("onlyYourSchool"));
        setLoading(false);
        return;
      }
      setIsSuperAdmin(superadmin);

      try {
        const data = await fetchSchoolEdit(moeCode);
        setSchool(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("failedToLoad"));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [moeCode, router, t]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-8 bg-gray-200 rounded w-2/3"></div>
          <div className="grid grid-cols-2 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-10 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-800 text-lg font-semibold">{t("accessDenied")}</p>
          <p className="text-red-600 mt-2">{error}</p>
          <Link
            href={schoolPath({ moe_code: moeCode })}
            className="inline-block mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            {t("backToSchool")}
          </Link>
        </div>
      </div>
    );
  }

  if (!school) return null;

  const breadcrumbItems = [
    { label: tc("home"), href: "/" },
    { label: school.state, href: `/?state=${encodeURIComponent(school.state)}` },
    { label: school.short_name || school.name, href: schoolPath(school) },
    { label: t("editBreadcrumb") },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("editTitle")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {school.short_name || school.name} ({school.moe_code})
          </p>
        </div>
        {school.claimed_at && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            {t("claimedBadge", {
              date: new Date(school.claimed_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
              }),
            })}
          </span>
        )}
      </div>

      <SchoolEditForm school={school} isSuperAdmin={isSuperAdmin} />
    </div>
  );
}
