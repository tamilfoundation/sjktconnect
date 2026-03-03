import HeroSection from "@/components/HeroSection";
import NationalStats from "@/components/NationalStats";
import SchoolMap from "@/components/SchoolMap";
import { fetchNationalStats } from "@/lib/api";

export default async function HomePage() {
  let stats = null;
  try {
    stats = await fetchNationalStats();
  } catch {
    // API may not be available during build — render with fallback
  }

  return (
    <>
      <HeroSection
        totalSchools={stats?.total_schools ?? 528}
        states={stats?.states ?? 12}
        constituencies={stats?.constituencies_with_schools ?? 150}
      />
      {stats && <NationalStats stats={stats} />}
      <div id="school-map">
        <SchoolMap />
      </div>
    </>
  );
}
