"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

export type ColourMode = "assistance" | "location" | "programmes" | "enrolment";

export interface FilterToggles {
  governmentAided: boolean;
  government: boolean;
  urban: boolean;
  rural: boolean;
  preschool: boolean;
  specialNeeds: boolean;
  both: boolean;
  none: boolean;
}

interface MapFilterPanelProps {
  colourMode: ColourMode;
  onColourModeChange: (mode: ColourMode) => void;
  toggles: FilterToggles;
  onToggleChange: (key: keyof FilterToggles) => void;
  enrolmentThreshold: number;
  onEnrolmentThresholdChange: (value: number) => void;
  onReset: () => void;
  filteredCount: number;
  totalCount: number;
}

const COLOUR_MODES: ColourMode[] = ["assistance", "location", "programmes", "enrolment"];

interface ToggleItem {
  key: keyof FilterToggles;
  labelKey: string;
  colour: string;
}

const TOGGLE_ITEMS: Record<string, ToggleItem[]> = {
  assistance: [
    { key: "governmentAided", labelKey: "governmentAided", colour: "#7c3aed" },
    { key: "government", labelKey: "government", colour: "#ea580c" },
  ],
  location: [
    { key: "urban", labelKey: "urban", colour: "#2563eb" },
    { key: "rural", labelKey: "rural", colour: "#16a34a" },
  ],
  programmes: [
    { key: "preschool", labelKey: "preschool", colour: "#7c3aed" },
    { key: "specialNeeds", labelKey: "specialNeeds", colour: "#2563eb" },
    { key: "both", labelKey: "both", colour: "#ea580c" },
    { key: "none", labelKey: "none", colour: "#6b7280" },
  ],
};

export default function MapFilterPanel({
  colourMode,
  onColourModeChange,
  toggles,
  onToggleChange,
  enrolmentThreshold,
  onEnrolmentThresholdChange,
  onReset,
  filteredCount,
  totalCount,
}: MapFilterPanelProps) {
  const t = useTranslations("mapFilters");
  const [isCollapsed, setIsCollapsed] = useState(true);

  // Expand by default on desktop, collapse on mobile
  useEffect(() => {
    setIsCollapsed(window.innerWidth < 768);
  }, []);

  const infoKey = `${colourMode}Info` as const;

  return (
    <div className="bg-white rounded-lg shadow-md">
      {/* Header — always visible */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer md:cursor-default"
        onClick={() => setIsCollapsed((prev) => !prev)}
      >
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-800">{t("filters")}</h3>
          {/* Collapse indicator — mobile only */}
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform md:hidden ${
              isCollapsed ? "" : "rotate-180"
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onReset();
          }}
          className="text-xs text-primary-600 hover:text-primary-800 font-medium"
        >
          {t("resetAll")}
        </button>
      </div>

      {/* Collapsible content */}
      <div className={`${isCollapsed ? "hidden" : "block"} md:block px-4 pb-4 space-y-4`}>
        {/* Colour By pills */}
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            {t("colourBy")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {COLOUR_MODES.map((mode) => (
              <button
                key={mode}
                onClick={() => onColourModeChange(mode)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                  colourMode === mode
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {t(mode)}
              </button>
            ))}
          </div>
        </div>

        {/* Toggle list or enrolment slider */}
        {colourMode === "enrolment" ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">0</span>
              <span className="text-sm font-semibold text-gray-800">
                ≤ {enrolmentThreshold}
              </span>
              <span className="text-xs text-gray-600">50</span>
            </div>
            <input
              type="range"
              min={0}
              max={50}
              value={enrolmentThreshold}
              onChange={(e) => onEnrolmentThresholdChange(Number(e.target.value))}
              className="w-full accent-red-600"
            />
            <p className="text-xs text-gray-500">
              {t("enrolmentThreshold", { value: enrolmentThreshold })}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {TOGGLE_ITEMS[colourMode]?.map((item) => (
              <label
                key={item.key}
                className="flex items-center justify-between cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: item.colour }}
                  />
                  <span className="text-sm text-gray-700 group-hover:text-gray-900">
                    {t(item.labelKey)}
                  </span>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={toggles[item.key]}
                    onChange={() => onToggleChange(item.key)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-gray-200 rounded-full peer peer-checked:bg-primary-600 transition-colors" />
                  <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                </div>
              </label>
            ))}
          </div>
        )}

        {/* Counter */}
        <p className="text-xs text-gray-500 pt-2 border-t border-gray-100">
          {t("showingSchools", { count: filteredCount, total: totalCount })}
        </p>

        {/* Info note */}
        <p className="text-xs text-gray-400 italic">
          {t(infoKey)}
        </p>
      </div>
    </div>
  );
}
