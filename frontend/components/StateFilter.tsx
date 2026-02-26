"use client";

interface StateFilterProps {
  states: string[];
  selectedState: string;
  onChange: (state: string) => void;
  schoolCount: number;
  totalCount: number;
}

export default function StateFilter({
  states,
  selectedState,
  onChange,
  schoolCount,
  totalCount,
}: StateFilterProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-3">
      <label
        htmlFor="state-filter"
        className="block text-xs font-semibold text-gray-700 mb-1"
      >
        Filter by State
      </label>
      <select
        id="state-filter"
        value={selectedState}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      >
        <option value="">All States</option>
        {states.map((state) => (
          <option key={state} value={state}>
            {state}
          </option>
        ))}
      </select>
      <p className="text-xs text-gray-500 mt-1">
        Showing {schoolCount} of {totalCount} schools
      </p>
    </div>
  );
}
