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
  try {
    [stats, schools] = await Promise.all([
      fetchNationalStats(),
      fetchMapSchools(),
    ]);
  } catch {
    // API may not be available during build — render with fallback
  }

  // Filter to schools with GPS coordinates on the server
  const mapSchools = schools.filter((s) => s.gps_lat && s.gps_lng);

  return (
    <>
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
