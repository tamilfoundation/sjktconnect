"use client";

import { useTranslations } from "next-intl";
import { SchoolDetail } from "@/lib/types";

interface SchoolProfileProps {
  school: SchoolDetail;
}

export default function SchoolProfile({ school }: SchoolProfileProps) {
  const t = useTranslations("schoolProfile");

  function formatAssistanceType(value: string): string {
    if (value === "SBK") return t("governmentAided");
    if (value === "SK") return t("government");
    return value;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          {t("schoolDetails")}
        </h2>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          {school.name_tamil && (
            <DetailRow label={t("tamilName")} value={school.name_tamil} />
          )}
          <DetailRow
            label={t("address")}
            value={
              [school.address, `${school.postcode} ${school.city}`, school.state]
                .filter(Boolean)
                .join(", ") || "—"
            }
          />
          {school.email && <DetailRow label={t("email")} value={school.email} />}
          {school.phone && <DetailRow label={t("phone")} value={school.phone} />}
          <DetailRow label={t("locationType")} value={school.location_type || "—"} />
          <DetailRow
            label={t("assistanceType")}
            value={formatAssistanceType(school.assistance_type) || "—"}
          />
          <DetailRow
            label={t("sessions")}
            value={
              school.session_count
                ? `${school.session_count} (${school.session_type || "—"})`
                : "—"
            }
          />
          <DetailRow
            label={t("school")}
            value={t("studentsCount", { count: school.enrolment ?? 0 })}
          />
          <DetailRow
            label={t("preschool")}
            value={t("studentsCount", { count: school.preschool_enrolment ?? 0 })}
          />
          <DetailRow
            label={t("specialNeeds")}
            value={t("studentsCount", { count: school.special_enrolment ?? 0 })}
          />
        </dl>
      </div>

      {school.leaders && school.leaders.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            {t("schoolLeadership")}
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

      {school.constituency_code && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            {t("politicalRepresentation")}
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
            <DetailRow
              label={t("constituency")}
              value={
                school.constituency_name
                  ? `${school.constituency_code} ${school.constituency_name}`
                  : school.constituency_code
              }
            />
            {school.dun_name && (
              <DetailRow
                label={t("dun")}
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
