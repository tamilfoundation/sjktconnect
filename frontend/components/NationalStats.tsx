"use client";

import { useTranslations } from "next-intl";
import { NationalStats as NationalStatsType } from "@/lib/types";

interface NationalStatsProps {
  stats: NationalStatsType;
}

export default function NationalStats({ stats }: NationalStatsProps) {
  const t = useTranslations("stats");

  const items = [
    { value: stats.total_students, label: t("totalStudents") },
    { value: stats.total_preschool, label: t("totalPreschool") },
    { value: stats.total_special_needs, label: t("totalSpecialNeeds") },
    { value: stats.total_teachers, label: t("totalTeachers") },
    { value: stats.schools_under_30_students, label: t("schoolsUnder30") },
  ];

  return (
    <section className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {items.map((item) => (
            <div key={item.label} className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-blue-900">
                {item.value.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500 mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
