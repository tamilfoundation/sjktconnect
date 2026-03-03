"use client";

import { useTranslations } from "next-intl";
import { NationalStats as NationalStatsType } from "@/lib/types";

interface NationalStatsProps {
  stats: NationalStatsType;
}

function formatImpactNumber(value: number): string {
  if (value >= 1000) {
    const floored = Math.floor(value / 1000) * 1000;
    if (floored === value) {
      return value.toLocaleString();
    }
    return floored.toLocaleString() + "+";
  }
  return value.toLocaleString();
}

export default function NationalStats({ stats }: NationalStatsProps) {
  const t = useTranslations("stats");

  const items = [
    {
      value: stats.total_students,
      label: t("totalStudents"),
      accent: "border-l-red-500",
    },
    {
      value: stats.total_preschool,
      label: t("totalPreschool"),
      accent: "border-l-blue-500",
    },
    {
      value: stats.total_special_needs,
      label: t("totalSpecialNeeds"),
      accent: "border-l-green-500",
    },
    {
      value: stats.total_teachers,
      label: t("totalTeachers"),
      accent: "border-l-amber-500",
    },
    {
      value: stats.schools_under_30_students,
      label: t("underEnrolled"),
      accent: "border-l-rose-500",
    },
  ];

  return (
    <section className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <h2 className="text-xs font-semibold tracking-widest text-gray-400 uppercase mb-4">
          {t("heading")}
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {items.map((item) => (
            <div
              key={item.label}
              className={`bg-gray-50 rounded-lg p-4 border-l-4 ${item.accent}`}
            >
              <div className="text-2xl sm:text-3xl font-bold text-blue-900">
                {formatImpactNumber(item.value)}
              </div>
              <div className="text-sm text-gray-500 mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
