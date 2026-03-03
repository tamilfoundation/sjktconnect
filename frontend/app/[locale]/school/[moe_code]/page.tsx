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
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-10 mb-6">
        {/* Photo — 7/12 width on desktop */}
        <div className="lg:col-span-7">
          <SchoolPhotoGallery
            images={school.images}
            imageUrl={school.image_url}
            schoolName={displayName}
          />
        </div>

        {/* Name + Stats — 5/12 width on desktop, top-aligned */}
        <div className="lg:col-span-5 flex flex-col justify-start">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 leading-tight mb-2">
            {displayName}
          </h1>
          {school.name_tamil && (
            <p className="text-lg text-gray-500 font-medium mb-3">{school.name_tamil}</p>
          )}
          <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-100 w-fit px-3 py-1.5 rounded-full mb-4">
            <span className="font-semibold text-primary-600">{school.moe_code}</span>
            <span>·</span>
            <span>{school.state}</span>
            <span>·</span>
            <span>PPD {school.ppd}</span>
          </div>
          <EditSchoolLink moeCode={school.moe_code} />

          {/* 3 Stat cards with icons */}
          <div className="grid grid-cols-3 gap-4 mb-4 mt-2">
            <StatCard
              label={t("studentsLabel")}
              value={school.enrolment ?? 0}
              icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" /></svg>}
            />
            <StatCard
              label={t("teachersLabel")}
              value={school.teacher_count ?? 0}
              icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" /></svg>}
            />
            <StatCard
              label={t("gradeLabel")}
              value={school.grade || "—"}
              icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" /></svg>}
              iconColor="text-yellow-500"
            />
          </div>

          {/* Preschool / Special Ed bar */}
          <div className="bg-primary-50 border border-primary-100 rounded-lg p-3 text-sm flex gap-4 justify-center text-primary-700">
            <div className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z" /></svg>
              <span>{t("preschoolLabel")}: <strong>{school.preschool_enrolment ?? 0}</strong></span>
            </div>
            <div className="w-px bg-primary-200 h-4 self-center" />
            <div className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" /></svg>
              <span>{t("specialEdLabel")}: <strong>{school.special_enrolment ?? 0}</strong></span>
            </div>
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
