import HeroSection from "@/components/HeroSection";
import NationalStats from "@/components/NationalStats";
import SchoolMap from "@/components/SchoolMap";
import { fetchMapSchools, fetchNationalStats } from "@/lib/api";

export const revalidate = 86400; // 24 hours — school data rarely changes

export default async function HomePage() {
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
        <SchoolMap initialSchools={mapSchools} />
      </div>
    </>
  );
}
