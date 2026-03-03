"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { School } from "@/lib/types";

interface ConstituencySchoolsProps {
  schools: School[];
  currentMoeCode: string;
  constituencyName: string;
}

export default function ConstituencySchools({
  schools,
  currentMoeCode,
  constituencyName,
}: ConstituencySchoolsProps) {
  const t = useTranslations("schoolProfile");
  const tc = useTranslations("common");
  const otherSchools = schools.filter((s) => s.moe_code !== currentMoeCode);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
        <div className="w-1 h-5 bg-primary-600 rounded-full" />
        <h2 className="text-lg font-semibold text-gray-800">
          {t("nearbySchools")}
        </h2>
      </div>
      <div className="p-6">
        {otherSchools.length === 0 ? (
          <p className="text-sm text-gray-500 italic">
            {t("noNearbySchools")}
          </p>
        ) : (
          <ul className="space-y-2">
            {otherSchools.map((school) => (
              <li key={school.moe_code}>
                <Link
                  href={`/school/${school.moe_code}`}
                  className="flex justify-between items-center text-sm hover:bg-gray-50 rounded px-2 py-1.5 -mx-2 transition-colors"
                >
                  <span className="text-primary-600 hover:text-primary-800">
                    {school.short_name || school.name}
                  </span>
                  <span className="text-gray-400 text-xs">
                    {school.enrolment?.toLocaleString() ?? "—"} {tc("students")}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
