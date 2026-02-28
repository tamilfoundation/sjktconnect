import { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  fetchSchoolDetail,
  fetchSchoolsByConstituency,
  fetchSchoolMentions,
} from "@/lib/api";
import Breadcrumb from "@/components/Breadcrumb";
import ClaimButton from "@/components/ClaimButton";
import EditSchoolLink from "@/components/EditSchoolLink";
import SchoolImage from "@/components/SchoolImage";
import SchoolProfile from "@/components/SchoolProfile";
import MiniMap from "@/components/MiniMap";
import MentionsSection from "@/components/MentionsSection";
import ConstituencySchools from "@/components/ConstituencySchools";

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
    const title = `${school.short_name || school.name} — SJK(T) Connect`;
    const description = `${school.short_name || school.name} (${school.moe_code}) in ${school.state}. Enrolment: ${school.enrolment?.toLocaleString() ?? "N/A"} students, ${school.teacher_count?.toLocaleString() ?? "N/A"} teachers. Grade ${school.grade || "N/A"}.`;

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

  // Fetch sidebar and mentions data in parallel
  const [constituencySchools, mentions] = await Promise.all([
    school.constituency_code
      ? fetchSchoolsByConstituency(school.constituency_code)
      : Promise.resolve([]),
    fetchSchoolMentions(school.moe_code),
  ]);

  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: school.state, href: `/?state=${encodeURIComponent(school.state)}` },
    { label: school.short_name || school.name },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <Breadcrumb items={breadcrumbItems} />

      {/* School Image */}
      {school.image_url && (
        <SchoolImage
          imageUrl={school.image_url}
          schoolName={school.short_name || school.name}
        />
      )}

      {/* School Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {school.short_name || school.name}
        </h1>
        {school.short_name && school.name !== school.short_name && (
          <p className="text-sm text-gray-500 mt-1">{school.name}</p>
        )}
        <p className="text-sm text-gray-500 mt-1">
          {school.moe_code} · {school.state} · {school.ppd}
        </p>
      </div>

      {/* Edit (if authenticated) or Claim CTA — above fold */}
      <div className="mb-6 flex flex-wrap gap-3 items-start">
        <ClaimButton moeCode={school.moe_code} />
        <EditSchoolLink moeCode={school.moe_code} />
      </div>

      {/* Main content: two-column layout on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: main profile */}
        <div className="lg:col-span-2 space-y-6">
          <SchoolProfile school={school} />

          {/* Mini Map */}
          {school.gps_lat && school.gps_lng && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Location
              </h2>
              <MiniMap
                lat={school.gps_lat}
                lng={school.gps_lng}
                schoolName={school.short_name || school.name}
              />
            </div>
          )}

          {/* Parliament Watch Mentions */}
          <MentionsSection mentions={mentions} />
        </div>

        {/* Right column: sidebar */}
        <div className="space-y-6">
          {school.constituency_code && school.constituency_name && (
            <ConstituencySchools
              schools={constituencySchools}
              currentMoeCode={school.moe_code}
              constituencyName={school.constituency_name}
            />
          )}
        </div>
      </div>
    </div>
  );
}
