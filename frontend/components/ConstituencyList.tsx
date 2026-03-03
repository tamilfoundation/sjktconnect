"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Constituency } from "@/lib/types";

interface ConstituencyListProps {
  constituencies: Constituency[];
  states: string[];
}

export default function ConstituencyList({
  constituencies,
  states,
}: ConstituencyListProps) {
  const t = useTranslations("constituency");
  const [selectedState, setSelectedState] = useState("");
  const [showAll, setShowAll] = useState(false);

  const stateFiltered = selectedState
    ? constituencies.filter((c) => c.state === selectedState)
    : constituencies;

  const filtered = showAll
    ? stateFiltered
    : stateFiltered.filter((c) => (c.school_count ?? 0) > 0);

  // Sort by school_count descending (most relevant first)
  const sorted = [...filtered].sort(
    (a, b) => (b.school_count ?? 0) - (a.school_count ?? 0)
  );

  const totalSchools = sorted.reduce(
    (sum, c) => sum + (c.school_count ?? 0),
    0
  );

  const withSchoolsCount = stateFiltered.filter(
    (c) => (c.school_count ?? 0) > 0
  ).length;

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <select
          value={selectedState}
          onChange={(e) => setSelectedState(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          aria-label={t("filterByState")}
        >
          <option value="">{t("allStates")}</option>
          {states.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setShowAll(!showAll)}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {showAll
            ? t("showWithSchools", { count: withSchoolsCount })
            : t("showAll", { count: stateFiltered.length })}
        </button>
        <span className="text-sm text-gray-500">
          {t("showingConstituencies", { count: sorted.length, total: totalSchools })}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left text-gray-500">
                <th className="px-4 py-3 font-medium">{t("codeCol")}</th>
                <th className="px-4 py-3 font-medium">{t("constituencyCol")}</th>
                <th className="px-4 py-3 font-medium">{t("stateCol")}</th>
                <th className="px-4 py-3 font-medium">{t("mpCol")}</th>
                <th className="px-4 py-3 font-medium">{t("partyCol")}</th>
                <th className="px-4 py-3 font-medium text-right">{t("schoolsCol")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sorted.map((c) => (
                <tr key={c.code} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-500 font-mono text-xs">
                    {c.code}
                  </td>
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/constituency/${c.code}`}
                      className="text-primary-600 hover:text-primary-800 hover:underline"
                    >
                      {c.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-gray-700">{c.state}</td>
                  <td className="px-4 py-2.5 text-gray-700">{c.mp_name}</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {c.mp_party}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-700">
                    {c.school_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
