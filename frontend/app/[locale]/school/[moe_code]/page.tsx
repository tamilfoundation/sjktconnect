import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  fetchSchoolDetail,
  fetchSchoolsByConstituency,
  fetchSchoolMentions,
  fetchSchoolNews,
} from "@/lib/api";
import Breadcrumb from "@/components/Breadcrumb";
import ClaimButton from "@/components/ClaimButton";
import EditSchoolLink from "@/components/EditSchoolLink";
import SchoolPhotoGallery from "@/components/SchoolImage";
import SchoolProfile from "@/components/SchoolProfile";
import StatCard from "@/components/StatCard";
import MiniMap from "@/components/MiniMap";
import MentionsSection from "@/components/MentionsSection";
import ConstituencySchools from "@/components/ConstituencySchools";
import NewsWatchSection from "@/components/NewsWatchSection";
import SchoolHistory from "@/components/SchoolHistory";
import { Link } from "@/i18n/navigation";

// ISR: revalidate every hour
export const revalidate = 3600;

interface PageProps {
  params: { moe_code: string };
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const school = await fetchSchoolDetail(params.moe_code);
    const name = school.short_name || school.name;
    const title = `${name} — SJK(T) Connect`;
    const description = `${name} (${school.moe_code}) in ${school.state}. Enrolment: ${school.enrolment?.toLocaleString() ?? "N/A"} students, ${school.teacher_count?.toLocaleString() ?? "N/A"} teachers. Grade ${school.grade || "N/A"}.`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
        siteName: "SJK(T) Connect",
      },
    };
  } catch {
    return {
      title: "School Not Found — SJK(T) Connect",
    };
  }
}

export default async function SchoolPage({ params }: PageProps) {
  let school;
  try {
    school = await fetchSchoolDetail(params.moe_code);
  } catch {
    notFound();
  }

  const displayName = school.short_name || school.name;

  const t = await getTranslations("schoolProfile");
  const tc = await getTranslations("common");

  const [constituencySchools, mentions, newsArticles] = await Promise.all([
    school.constituency_code
      ? fetchSchoolsByConstituency(school.constituency_code)
      : Promise.resolve([]),
    fetchSchoolMentions(school.moe_code),
    fetchSchoolNews(school.moe_code),
  ]);

  const breadcrumbItems = [
    { label: tc("home"), href: "/" },
    { label: school.state, href: `/?state=${encodeURIComponent(school.state)}` },
    { label: displayName },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb items={breadcrumbItems} />

      {/* Hero: Side-by-side on desktop, stacked on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
        {/* Photo — 3/5 width on desktop */}
        <div className="lg:col-span-3">
          <SchoolPhotoGallery
            images={school.images}
            imageUrl={school.image_url}
            schoolName={displayName}
          />
        </div>

        {/* Name + Stats — 2/5 width on desktop */}
        <div className="lg:col-span-2 flex flex-col justify-center space-y-3">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
            {displayName}
          </h1>
          {school.name_tamil && (
            <p className="text-lg text-gray-700">{school.name_tamil}</p>
          )}
          <p className="text-sm text-gray-500">
            {school.moe_code} · {school.state} · {school.ppd}
          </p>
          <EditSchoolLink moeCode={school.moe_code} />

          {/* Stat cards — up to 5 */}
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 pt-2">
            <StatCard
              label={t("studentsLabel")}
              value={school.enrolment ?? 0}
            />
            <StatCard label={t("teachersLabel")} value={school.teacher_count ?? 0} />
            <StatCard label={t("gradeLabel")} value={school.grade || "—"} />
            <StatCard label={t("preschoolLabel")} value={school.preschool_enrolment ?? 0} />
            <StatCard label={t("specialEdLabel")} value={school.special_enrolment ?? 0} />
          </div>
        </div>
      </div>

      {/* Main content: two-column layout on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: main content */}
        <div className="lg:col-span-2 space-y-6">
          <SchoolProfile school={school} />

          {/* Parliament Watch Mentions */}
          <MentionsSection mentions={mentions} />

          {/* News Watch */}
          <NewsWatchSection articles={newsArticles} />

          {/* School History CTA */}
          <SchoolHistory />
        </div>

        {/* Right column: sidebar */}
        <div className="space-y-6">
          {/* Constituency & DUN card */}
          {school.constituency_code && (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
                <div className="w-1 h-5 bg-primary-600 rounded-full" />
                <h2 className="text-lg font-semibold text-gray-800">
                  {t("politicalRepresentation")}
                </h2>
              </div>
              <div className="p-6 space-y-4">
                {/* Constituency link */}
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{t("constituency")}</p>
                  <Link
                    href={`/constituency/${school.constituency_code}`}
                    className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-800 font-medium text-sm transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                    </svg>
                    {school.constituency_code} {school.constituency_name}
                  </Link>
                </div>
                {/* DUN link */}
                {school.dun_name && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{t("dun")}</p>
                    {school.dun_id ? (
                      <Link
                        href={`/dun/${school.dun_id}`}
                        className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-800 font-medium text-sm transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                        </svg>
                        {school.dun_code} {school.dun_name}
                      </Link>
                    ) : (
                      <p className="text-sm text-gray-800 font-medium">
                        {school.dun_code} {school.dun_name}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Location (MiniMap) */}
          {school.gps_lat && school.gps_lng && (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
                <div className="w-1 h-5 bg-primary-600 rounded-full" />
                <h2 className="text-lg font-semibold text-gray-800">
                  {t("location")}
                </h2>
              </div>
              <div className="p-4">
                <MiniMap
                  lat={school.gps_lat}
                  lng={school.gps_lng}
                  schoolName={displayName}
                />
              </div>
            </div>
          )}

          {/* Schools in the same constituency */}
          {school.constituency_code && school.constituency_name && (
            <ConstituencySchools
              schools={constituencySchools}
              currentMoeCode={school.moe_code}
              constituencyName={school.constituency_name}
            />
          )}
        </div>
      </div>

      {/* Claim button — bottom of page */}
      <div className="mt-8">
        <ClaimButton moeCode={school.moe_code} />
      </div>
    </div>
  );
}
