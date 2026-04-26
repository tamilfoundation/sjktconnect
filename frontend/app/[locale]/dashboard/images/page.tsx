"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";
import { searchEntities } from "@/lib/api";
import ImageManager from "@/components/ImageManager";

type SchoolHit = {
  moe_code: string;
  short_name?: string | null;
  name?: string;
};

export default function DashboardImagesPage() {
  const t = useTranslations("suggestions");
  const { status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const searchParams = useSearchParams();
  const initialMoe = searchParams.get("school") || "";
  const [selectedMoe, setSelectedMoe] = useState<string>(initialMoe);
  const [selectedLabel, setSelectedLabel] = useState<string>("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SchoolHit[]>([]);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  // Bound school admin: jump straight to their school.
  useEffect(() => {
    if (!profile) return;
    if (profile.role !== "SUPERADMIN" && profile.admin_school) {
      setSelectedMoe(profile.admin_school.moe_code);
      setSelectedLabel(profile.admin_school.name);
    }
  }, [profile]);

  // Picker search debounced.
  useEffect(() => {
    if (profile?.role !== "SUPERADMIN") return;
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      searchEntities(query.trim()).then((r) => {
        if (cancelled) return;
        setHits(r.schools as SchoolHit[]);
      });
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, profile?.role]);

  const isSuperadmin = profile?.role === "SUPERADMIN";
  const canManage = useMemo(
    () => Boolean(profile && (isSuperadmin || profile.admin_school)),
    [profile, isSuperadmin],
  );

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

  if (!canManage) {
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

      {isSuperadmin ? (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            School
          </label>
          {selectedMoe ? (
            <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-3 py-2">
              <span className="text-sm text-gray-900">
                {selectedLabel || selectedMoe}
              </span>
              <button
                onClick={() => {
                  setSelectedMoe("");
                  setSelectedLabel("");
                  setQuery("");
                }}
                className="text-xs text-primary-600 hover:underline ml-auto"
              >
                Change
              </button>
            </div>
          ) : (
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by school name or MOE code…"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              {hits.length > 0 && (
                <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                  {hits.map((h) => (
                    <li key={h.moe_code}>
                      <button
                        onClick={() => {
                          setSelectedMoe(h.moe_code);
                          setSelectedLabel(h.short_name || h.name || h.moe_code);
                        }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                      >
                        <span className="font-medium">{h.short_name || h.name}</span>
                        <span className="text-gray-500 ml-2">{h.moe_code}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-500 mb-8">
          {profile.admin_school?.name}
        </p>
      )}

      {selectedMoe ? (
        <ImageManager moeCode={selectedMoe} />
      ) : (
        <div className="text-center py-12 text-gray-500 text-sm">
          Select a school above to manage its images.
        </div>
      )}
    </div>
  );
}
