"use client";

import { useTranslations } from "next-intl";
import { SchoolDetail } from "@/lib/types";
import { isEmpty } from "@/lib/translations";

interface SchoolProfileProps {
  school: SchoolDetail;
}

export default function SchoolProfile({ school }: SchoolProfileProps) {
  const t = useTranslations("schoolProfile");

  return (
    <div className="space-y-6">
      {/* School Details */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
          <div className="w-1 h-5 bg-primary-600 rounded-full" />
          <h2 className="text-lg font-semibold text-gray-800">
            {t("schoolDetails")}
          </h2>
        </div>
        <div className="p-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
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
            {!isEmpty(school.phone) && (
              <DetailRow label={t("phone")} value={school.phone} />
            )}
            {!isEmpty(school.location_type) && (
              <DetailRow
                label={t("locationType")}
                value={t.has(`location_${school.location_type}`) ? t(`location_${school.location_type}`) : school.location_type}
              />
            )}
            <DetailRow
              label={t("assistanceType")}
              value={t.has(`assistance_${school.assistance_type}`) ? t(`assistance_${school.assistance_type}`) : school.assistance_type || "—"}
            />
            {!isEmpty(school.session_type) && (
              <DetailRow
                label={t("sessions")}
                value={t.has(`session_${school.session_type}`) ? t(`session_${school.session_type}`) : school.session_type}
              />
            )}
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
          <p className="text-xs text-gray-400 mt-4 pt-3 border-t border-gray-100">
            {t("dataSource")}
          </p>
        </div>
      </div>

      {/* Leadership — always shown */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
          <div className="w-1 h-5 bg-primary-600 rounded-full" />
          <h2 className="text-lg font-semibold text-gray-800">
            {t("schoolLeadership")}
          </h2>
        </div>
        <div className="p-6">
          {school.leaders && school.leaders.length > 0 ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
              {school.leaders.map((leader) => (
                <LeaderRow
                  key={leader.role}
                  role={leader.role_display}
                  name={leader.name}
                />
              ))}
            </dl>
          ) : (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
              <LeaderRow role={t("headmaster")} name={t("notAvailable")} />
              <LeaderRow role={t("ptaChairman")} name={t("notAvailable")} />
            </dl>
          )}
        </div>
      </div>
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

function LeaderRow({ role, name }: { role: string; name: string }) {
  const isUnavailable = name === "Not Available" || name === "Tiada Maklumat" || name === "தகவல் இல்லை";
  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 mt-0.5">
        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
      </div>
      <div>
        <dt className="text-gray-500 text-sm">{role}</dt>
        <dd className={`font-medium mt-0.5 text-sm ${isUnavailable ? "text-gray-400 italic" : "text-gray-800"}`}>
          {name}
        </dd>
      </div>
    </div>
  );
}
