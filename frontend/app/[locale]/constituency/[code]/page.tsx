import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  fetchConstituencyDetail,
  fetchConstituencyGeoJSON,
  fetchDUNs,
} from "@/lib/api";
import Breadcrumb from "@/components/Breadcrumb";
import StatCard from "@/components/StatCard";
import ScorecardCard from "@/components/ScorecardCard";
import DemographicsCard from "@/components/DemographicsCard";
import SchoolTable from "@/components/SchoolTable";
import BoundaryMap from "@/components/BoundaryMap";
import { Link } from "@/i18n/navigation";

export const revalidate = 3600;

interface PageProps {
  params: { code: string };
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const c = await fetchConstituencyDetail(params.code);
    const title = `${c.code} ${c.name} — SJK(T) Connect`;
    const description = `${c.mp_name} (${c.mp_party}) represents ${c.name} constituency in ${c.state}. ${c.schools.length} Tamil school${c.schools.length !== 1 ? "s" : ""}.`;
    return {
      title,
      description,
      openGraph: { title, description, type: "website", siteName: "SJK(T) Connect" },
    };
  } catch {
    const t = await getTranslations("constituency");
    return { title: t("notFoundTitle") };
  }
}

export default async function ConstituencyPage({ params }: PageProps) {
  const t = await getTranslations("constituency");
  const tc = await getTranslations("common");
  let constituency;
  try {
    constituency = await fetchConstituencyDetail(params.code);
  } catch {
    notFound();
  }

  const [geoJSON, duns] = await Promise.all([
    fetchConstituencyGeoJSON(params.code),
    fetchDUNs({ constituency: params.code }),
  ]);

  const totalEnrolment = constituency.schools.reduce(
    (sum, s) => sum + (s.enrolment ?? 0),
    0
  );
  const totalTeachers = constituency.schools.reduce(
    (sum, s) => sum + (s.teacher_count ?? 0),
    0
  );

  // Estimate map centre from school GPS coordinates
  const schoolsWithGPS = constituency.schools.filter(
    (s) => s.gps_lat && s.gps_lng
  );
  const center =
    schoolsWithGPS.length > 0
      ? {
          lat:
            schoolsWithGPS.reduce((sum, s) => sum + s.gps_lat!, 0) /
            schoolsWithGPS.length,
          lng:
            schoolsWithGPS.reduce((sum, s) => sum + s.gps_lng!, 0) /
            schoolsWithGPS.length,
        }
      : { lat: 4.2105, lng: 101.9758 };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[
          { label: tc("home"), href: "/" },
          { label: t("title"), href: "/constituencies" },
          { label: `${constituency.code} ${constituency.name}` },
        ]}
      />

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {constituency.code} {constituency.name}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {constituency.state} · {t("mp")} {constituency.mp_name} ({constituency.mp_party}
          {constituency.mp_coalition
            ? ` / ${constituency.mp_coalition}`
            : ""}
          )
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard label={t("tamilSchools")} value={constituency.schools.length} />
        <StatCard label={t("totalStudents")} value={totalEnrolment} />
        <StatCard label={t("totalTeachers")} value={totalTeachers} />
        <StatCard label={t("duns")} value={duns.length} />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Boundary Map */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              {t("boundary")}
            </h2>
            <BoundaryMap geoJSON={geoJSON} center={center} />
          </div>

          {/* School Table */}
          <SchoolTable schools={constituency.schools} />
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Scorecard */}
          <ScorecardCard
            scorecard={constituency.scorecard}
            mpName={constituency.mp_name}
          />

          {/* Demographics */}
          <DemographicsCard
            indianPopulation={constituency.indian_population}
            indianPercentage={constituency.indian_percentage}
            avgIncome={constituency.avg_income}
            povertyRate={constituency.poverty_rate}
            gini={constituency.gini}
            unemploymentRate={constituency.unemployment_rate}
          />

          {/* DUN list */}
          {duns.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                {t("stateConstituencies")}
              </h2>
              <ul className="space-y-2">
                {duns.map((dun) => (
                  <li key={dun.id}>
                    <Link
                      href={`/dun/${dun.id}`}
                      className="flex justify-between items-center text-sm hover:bg-gray-50 rounded px-2 py-1.5 -mx-2 transition-colors"
                    >
                      <span className="text-primary-600 hover:text-primary-800">
                        {dun.code} {dun.name}
                      </span>
                      <span className="text-gray-400 text-xs">
                        {dun.adun_name || "—"}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
