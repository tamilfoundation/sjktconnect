import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { fetchDUNDetail, fetchDUNGeoJSON } from "@/lib/api";
import Breadcrumb from "@/components/Breadcrumb";
import StatCard from "@/components/StatCard";
import DemographicsCard from "@/components/DemographicsCard";
import SchoolTable from "@/components/SchoolTable";
import BoundaryMap from "@/components/BoundaryMap";
import { Link } from "@/i18n/navigation";

export const revalidate = 3600;

interface PageProps {
  params: { id: string };
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const dun = await fetchDUNDetail(parseInt(params.id, 10));
    const title = `${dun.code} ${dun.name} — SJK(T) Connect`;
    const description = `${dun.name} (${dun.code}) state constituency in ${dun.state}. ${dun.schools.length} Tamil school${dun.schools.length !== 1 ? "s" : ""}.${dun.adun_name ? ` ADUN: ${dun.adun_name}` : ""}`;
    return {
      title,
      description,
      openGraph: { title, description, type: "website", siteName: "SJK(T) Connect" },
    };
  } catch {
    const t = await getTranslations("constituency");
    return { title: t("dunNotFoundTitle") };
  }
}

export default async function DUNPage({ params }: PageProps) {
  const t = await getTranslations("constituency");
  const tc = await getTranslations("common");
  const dunId = parseInt(params.id, 10);
  if (isNaN(dunId)) {
    notFound();
  }

  let dun;
  try {
    dun = await fetchDUNDetail(dunId);
  } catch {
    notFound();
  }

  const geoJSON = await fetchDUNGeoJSON(dunId);

  const totalEnrolment = dun.schools.reduce(
    (sum, s) => sum + (s.enrolment ?? 0),
    0
  );
  const totalTeachers = dun.schools.reduce(
    (sum, s) => sum + (s.teacher_count ?? 0),
    0
  );

  const schoolsWithGPS = dun.schools.filter((s) => s.gps_lat && s.gps_lng);
  const center =
    schoolsWithGPS.length > 0
      ? {
          lat:
            schoolsWithGPS.reduce((sum, s) => sum + Number(s.gps_lat), 0) /
            schoolsWithGPS.length,
          lng:
            schoolsWithGPS.reduce((sum, s) => sum + Number(s.gps_lng), 0) /
            schoolsWithGPS.length,
        }
      : { lat: 4.2105, lng: 101.9758 };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb
        items={[
          { label: tc("home"), href: "/" },
          { label: t("title"), href: "/constituencies" },
          {
            label: `${dun.constituency_code} ${dun.constituency_name}`,
            href: `/constituency/${dun.constituency_code}`,
          },
          { label: `${dun.code} ${dun.name}` },
        ]}
      />

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {dun.code} {dun.name}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {dun.state} · {t("parliament")} {dun.constituency_code}{" "}
          {dun.constituency_name}
          {dun.adun_name
            ? ` · ${t("adun")} ${dun.adun_name} (${dun.adun_party}${dun.adun_coalition ? ` / ${dun.adun_coalition}` : ""})`
            : ""}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
        <StatCard label={t("tamilSchools")} value={dun.schools.length} />
        <StatCard label={t("totalStudents")} value={totalEnrolment} />
        <StatCard label={t("totalTeachers")} value={totalTeachers} />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              {t("boundary")}
            </h2>
            <BoundaryMap geoJSON={geoJSON} center={center} />
          </div>
          <SchoolTable schools={dun.schools} />
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <DemographicsCard
            indianPopulation={dun.indian_population}
            indianPercentage={dun.indian_percentage}
          />

          {/* Back to constituency */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              {t("parliamentConstituency")}
            </h2>
            <Link
              href={`/constituency/${dun.constituency_code}`}
              className="text-primary-600 hover:text-primary-800 hover:underline text-sm"
            >
              {dun.constituency_code} {dun.constituency_name} →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
