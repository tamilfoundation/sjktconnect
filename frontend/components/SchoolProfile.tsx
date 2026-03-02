import { SchoolDetail } from "@/lib/types";

interface SchoolProfileProps {
  school: SchoolDetail;
}

function formatAssistanceType(value: string): string {
  if (value === "SBK") return "Government-Aided (SBK)";
  if (value === "SK") return "Government (SK)";
  return value;
}

export default function SchoolProfile({ school }: SchoolProfileProps) {
  return (
    <div className="space-y-6">
      {/* School Details */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          School Details
        </h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {school.name_tamil && (
            <DetailRow label="Tamil Name" value={school.name_tamil} />
          )}
          <DetailRow
            label="Address"
            value={
              [school.address, `${school.postcode} ${school.city}`, school.state]
                .filter(Boolean)
                .join(", ") || "—"
            }
          />
          {school.email && <DetailRow label="Email" value={school.email} />}
          {school.phone && <DetailRow label="Phone" value={school.phone} />}
          <DetailRow label="Location Type" value={school.location_type || "—"} />
          <DetailRow
            label="Assistance Type"
            value={formatAssistanceType(school.assistance_type) || "—"}
          />
          <DetailRow
            label="Sessions"
            value={
              school.session_count
                ? `${school.session_count} (${school.session_type || "—"})`
                : "—"
            }
          />
          <DetailRow
            label="School"
            value={`${school.enrolment ?? 0} students`}
          />
          <DetailRow
            label="Preschool"
            value={`${school.preschool_enrolment ?? 0} students`}
          />
          <DetailRow
            label="Special Needs"
            value={`${school.special_enrolment ?? 0} students`}
          />
        </dl>
      </div>

      {/* School Leadership */}
      {school.leaders && school.leaders.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            School Leadership
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
            {school.leaders.map((leader) => (
              <DetailRow
                key={leader.role}
                label={leader.role_display}
                value={leader.name}
              />
            ))}
          </dl>
        </div>
      )}

      {/* Political Representation */}
      {school.constituency_code && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Political Representation
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
            <DetailRow
              label="Constituency"
              value={
                school.constituency_name
                  ? `${school.constituency_code} ${school.constituency_name}`
                  : school.constituency_code
              }
            />
            {school.dun_name && (
              <DetailRow
                label="DUN"
                value={
                  school.dun_code
                    ? `${school.dun_code} ${school.dun_name}`
                    : school.dun_name
                }
              />
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-gray-800 font-medium mt-0.5">{value}</dd>
    </div>
  );
}
