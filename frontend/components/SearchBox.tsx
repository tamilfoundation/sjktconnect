"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { searchEntities } from "@/lib/api";
import { School, Constituency } from "@/lib/types";

interface SearchBoxProps {
  onSelect: (school: School) => void;
  onClear: () => void;
}

export default function SearchBox({ onSelect, onClear }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{
    schools: School[];
    constituencies: Constituency[];
  } | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  const handleChange = useCallback(
    (value: string) => {
      setQuery(value);

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      if (value.length < 2) {
        setResults(null);
        setIsOpen(false);
        if (value.length === 0) {
          onClear();
        }
        return;
      }

      debounceRef.current = setTimeout(async () => {
        setLoading(true);
        try {
          const data = await searchEntities(value);
          setResults(data);
          setIsOpen(true);
        } catch {
          setResults(null);
        } finally {
          setLoading(false);
        }
      }, 300);
    },
    [onClear]
  );

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectSchool = useCallback(
    (school: School) => {
      setQuery(school.short_name || school.name);
      setIsOpen(false);
      onSelect(school);
    },
    [onSelect]
  );

  const handleClear = useCallback(() => {
    setQuery("");
    setResults(null);
    setIsOpen(false);
    onClear();
  }, [onClear]);

  const hasResults =
    results &&
    (results.schools.length > 0 || results.constituencies.length > 0);

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Search schools or constituencies..."
          className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm shadow-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          aria-label="Search schools"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Clear search"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {loading && (
          <div className="absolute right-8 top-1/2 -translate-y-1/2">
            <div className="animate-spin h-4 w-4 border-2 border-primary-500 border-t-transparent rounded-full" />
          </div>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && results && (
        <div className="absolute top-full mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto z-50">
          {!hasResults && (
            <p className="px-3 py-2 text-sm text-gray-500">No results found</p>
          )}

          {results.schools.length > 0 && (
            <div>
              <p className="px-3 py-1.5 text-xs font-semibold text-gray-500 bg-gray-50">
                Schools ({results.schools.length})
              </p>
              {results.schools.map((school) => (
                <div
                  key={school.moe_code}
                  className="flex items-center justify-between px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-0"
                >
                  <button
                    onClick={() => handleSelectSchool(school)}
                    className="text-left flex-1 min-w-0"
                  >
                    <p className="text-sm font-medium text-gray-800">
                      {school.short_name || school.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {school.moe_code} &middot; {school.state}
                      {school.enrolment > 0 &&
                        ` \u00b7 ${school.enrolment} students`}
                    </p>
                  </button>
                  <a
                    href={`/school/${school.moe_code}`}
                    className="ml-2 text-xs text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap"
                  >
                    View →
                  </a>
                </div>
              ))}
            </div>
          )}

          {results.constituencies.length > 0 && (
            <div>
              <p className="px-3 py-1.5 text-xs font-semibold text-gray-500 bg-gray-50">
                Constituencies ({results.constituencies.length})
              </p>
              {results.constituencies.map((c) => (
                <a
                  key={c.code}
                  href={`/constituency/${c.code}`}
                  className="block px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-0"
                >
                  <p className="text-sm font-medium text-gray-800">
                    {c.code} {c.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {c.mp_name} ({c.mp_party}) &middot; {c.school_count} schools
                  </p>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
