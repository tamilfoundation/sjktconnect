"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchSchoolEdit, fetchMe } from "@/lib/api";
import { SchoolEditData } from "@/lib/types";
import Breadcrumb from "@/components/Breadcrumb";
import SchoolEditForm from "@/components/SchoolEditForm";

export default function SchoolEditPage() {
  const params = useParams();
  const router = useRouter();
  const moeCode = params.moe_code as string;

  const [school, setSchool] = useState<SchoolEditData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      // Check authentication first
      const user = await fetchMe();
      if (!user) {
        router.push(`/claim?school=${moeCode}`);
        return;
      }
      if (user.school_moe_code !== moeCode) {
        setError("You can only edit your own school.");
        setLoading(false);
        return;
      }

      try {
        const data = await fetchSchoolEdit(moeCode);
        setSchool(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load school data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [moeCode, router]);

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
          <p className="text-red-800 text-lg font-semibold">Access Denied</p>
          <p className="text-red-600 mt-2">{error}</p>
          <a
            href={`/school/${moeCode}`}
            className="inline-block mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Back to School Page
          </a>
        </div>
      </div>
    );
  }

  if (!school) return null;

  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: school.state, href: `/?state=${encodeURIComponent(school.state)}` },
    { label: school.short_name || school.name, href: `/school/${school.moe_code}` },
    { label: "Edit" },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Edit School Data
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {school.short_name || school.name} ({school.moe_code})
        </p>
      </div>

      <SchoolEditForm school={school} />
    </div>
  );
}
