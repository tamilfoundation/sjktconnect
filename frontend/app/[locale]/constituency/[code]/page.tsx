import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  fetchConstituencyDetail,
  fetchConstituencyGeoJSON,
  fetchConstituencyMentions,
  fetchDUNs,
} from "@/lib/api";
import Breadcrumb from "@/components/Breadcrumb";
import StatCard from "@/components/StatCard";
import ScorecardCard from "@/components/ScorecardCard";
import ElectoralInfluenceCard from "@/components/ElectoralInfluenceCard";
import SchoolTable from "@/components/SchoolTable";
import BoundaryMap from "@/components/BoundaryMap";
import MentionsList from "@/components/MentionsList";
import ContactMPCard from "@/components/ContactMPCard";
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

  const [geoJSON, duns, mentions] = await Promise.all([
    fetchConstituencyGeoJSON(params.code),
    fetchDUNs({ constituency: params.code }),
    fetchConstituencyMentions(params.code),
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
          { label: constituency.state, href: `/constituencies?state=${encodeURIComponent(constituency.state)}` },
          { label: `${constituency.code} ${constituency.name}` },
        ]}
      />

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900">
          {constituency.code} {constituency.name}
        </h1>
        <div className="flex items-center gap-3 mt-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-amber-600 text-white uppercase tracking-wide">
            {constituency.mp_party.replace("(", " (")}
          </span>
          <span className="text-sm text-gray-600">
            YB {constituency.mp_name}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard
          label={t("tamilSchools")}
          value={constituency.schools.length}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342" />
            </svg>
          }
        />
        <StatCard
          label={t("totalStudents")}
          value={totalEnrolment}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
            </svg>
          }
        />
        <StatCard
          label={t("totalTeachers")}
          value={totalTeachers}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
          }
        />
        <StatCard
          label={t("duns")}
          value={duns.length}
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
            </svg>
          }
        />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Boundary Map — only show when boundary data exists */}
          {geoJSON && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                {t("boundary")}
              </h2>
              <BoundaryMap geoJSON={geoJSON} center={center} />
            </div>
          )}

          {/* School Table */}
          <SchoolTable schools={constituency.schools} />

          {/* Hansard Mentions */}
          {mentions.length > 0 && (
            <MentionsList
              mentions={mentions}
              title={t("hansardMentions")}
            />
          )}
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Contact Your MP */}
          <ContactMPCard
            mp={constituency.mp}
            constituencyCode={constituency.code}
            constituencyName={constituency.name}
          />

          {/* Electoral Influence */}
          <ElectoralInfluenceCard
            influence={constituency.electoral_influence}
            constituencyName={constituency.name}
            constituencyCode={constituency.code}
            state={constituency.state}
          />

          {/* Scorecard */}
          <ScorecardCard
            scorecard={constituency.scorecard}
            mpName={constituency.mp_name}
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
