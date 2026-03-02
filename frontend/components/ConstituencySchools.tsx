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
  const t = useTranslations("constituency");
  const tc = useTranslations("common");
  const otherSchools = schools.filter((s) => s.moe_code !== currentMoeCode);

  if (otherSchools.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">
        {t("schoolsIn", { name: constituencyName })}
      </h2>
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
    </div>
  );
}
