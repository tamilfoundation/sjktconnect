import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import HeroSection from "@/components/HeroSection";
import NationalStats from "@/components/NationalStats";
import SchoolMap from "@/components/SchoolMap";
import { fetchMapSchools, fetchNationalStats } from "@/lib/api";

export const revalidate = 86400;

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default async function HomePage({ params }: PageProps) {
  const { locale } = await params;
  setRequestLocale(locale);
  let stats = null;
  let schools: Awaited<ReturnType<typeof fetchMapSchools>> = [];
  let apiFailed = false;
  try {
    [stats, schools] = await Promise.all([
      fetchNationalStats(),
      fetchMapSchools(),
    ]);
  } catch (err) {
    // Audit 2026-07-01: previously an empty catch silently rendered the
    // baseline 528/12/150 counts, hiding a real API outage from admin.
    // Log to the server console (Cloud Run captures it) and flag the
    // page so a visible banner tells visitors data is degraded.
    apiFailed = true;
    console.error("HomePage: API unavailable — rendering with fallback stats", err);
  }

  // Filter to schools with GPS coordinates on the server
  const mapSchools = schools.filter((s) => s.gps_lat && s.gps_lng);

  return (
    <>
      {apiFailed && (
        <div
          role="status"
          className="bg-amber-50 border-b border-amber-200 text-amber-900 text-sm text-center py-2 px-4"
        >
          Live statistics unavailable right now. Showing recent baseline numbers.
        </div>
      )}
      <HeroSection
        totalSchools={stats?.total_schools ?? 528}
        states={stats?.states ?? 12}
        constituencies={stats?.constituencies_with_schools ?? 150}
      />
      {stats && <NationalStats stats={stats} />}
      <div id="school-map">
        {/* Suspense boundary required by Next 14+ when a client child uses
            useSearchParams (the SchoolMap state-filter URL param reader). */}
        <Suspense fallback={null}>
          <SchoolMap initialSchools={mapSchools} />
        </Suspense>
      </div>
    </>
  );
}
