"use client";

import { useState } from "react";
import Link from "next/link";
import { Constituency } from "@/lib/types";

interface ConstituencyListProps {
  constituencies: Constituency[];
  states: string[];
}

export default function ConstituencyList({
  constituencies,
  states,
}: ConstituencyListProps) {
  const [selectedState, setSelectedState] = useState("");

  const filtered = selectedState
    ? constituencies.filter((c) => c.state === selectedState)
    : constituencies;

  const totalSchools = filtered.reduce(
    (sum, c) => sum + (c.school_count ?? 0),
    0
  );

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <select
          value={selectedState}
          onChange={(e) => setSelectedState(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          aria-label="Filter by state"
        >
          <option value="">All States</option>
          {states.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
        <span className="text-sm text-gray-500">
          Showing {filtered.length} constituencies · {totalSchools} Tamil
          schools
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Code</th>
                <th className="px-4 py-3 font-medium">Constituency</th>
                <th className="px-4 py-3 font-medium">State</th>
                <th className="px-4 py-3 font-medium">MP</th>
                <th className="px-4 py-3 font-medium">Party</th>
                <th className="px-4 py-3 font-medium text-right">Schools</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((c) => (
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
