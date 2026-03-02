"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { School } from "@/lib/types";

interface SchoolTableProps {
  schools: School[];
}

export default function SchoolTable({ schools }: SchoolTableProps) {
  const t = useTranslations("constituency");
  if (schools.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          {t("tamilSchools")}
        </h2>
        <p className="text-sm text-gray-500">
          {t("noSchools")}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        {t("tamilSchools")} ({schools.length})
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="pb-2 pr-4 font-medium">{t("schoolCol")}</th>
              <th className="pb-2 pr-4 font-medium text-right">{t("studentsCol")}</th>
              <th className="pb-2 pr-4 font-medium text-right">{t("teachersCol")}</th>
              <th className="pb-2 font-medium">{t("ppdCol")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {schools.map((school) => (
              <tr key={school.moe_code} className="hover:bg-gray-50">
                <td className="py-2 pr-4">
                  <Link
                    href={`/school/${school.moe_code}`}
                    className="text-primary-600 hover:text-primary-800 hover:underline"
                  >
                    {school.short_name || school.name}
                  </Link>
                  <span className="block text-xs text-gray-400">
                    {school.moe_code}
                  </span>
                </td>
                <td className="py-2 pr-4 text-right text-gray-700">
                  {school.enrolment?.toLocaleString() ?? "—"}
                </td>
                <td className="py-2 pr-4 text-right text-gray-700">
                  {school.teacher_count?.toLocaleString() ?? "—"}
                </td>
                <td className="py-2 text-gray-700">{school.ppd}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
