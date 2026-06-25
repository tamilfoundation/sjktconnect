"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { APIProvider, Map, useMap } from "@vis.gl/react-google-maps";
import SchoolMarkers from "./SchoolMarkers";
import MapFilterPanel, {
  ColourMode,
  FilterToggles,
} from "./MapFilterPanel";
import SearchBox from "./SearchBox";
import { Link } from "@/i18n/navigation";
import { School } from "@/lib/types";

const MALAYSIA_CENTER = { lat: 4.2105, lng: 101.9758 };
const DEFAULT_ZOOM = 7;
const SINGLE_SCHOOL_ZOOM = 13;
const FIT_BOUNDS_PADDING = 60;

/**
 * Filter the school list by `state` URL param (case-insensitive).
 * Exported as a pure function for unit testing without React/map setup.
 */
export function filterByStateParam(
  schools: School[],
  stateParam: string | null,
): School[] {
  if (!stateParam) return schools;
  const needle = stateParam.toLowerCase().trim();
  return schools.filter((s) => (s.state ?? "").toLowerCase() === needle);
}

/**
 * Inside-the-Map child component that auto-fits bounds to the visible school
 * set when the bounds-key changes (typically the state filter changing).
 * Must be a child of <Map> so useMap() can resolve. Returns null — render-free.
 */
function FitBoundsOnStateFilter({
  schools,
  boundsKey,
}: {
  schools: School[];
  boundsKey: string;
}) {
  const map = useMap();
  useEffect(() => {
    if (!map || !boundsKey || schools.length === 0) return;
    if (typeof google === "undefined" || !google.maps?.LatLngBounds) return;
    const coords = schools
      .map((s) => ({ lat: s.gps_lat ?? null, lng: s.gps_lng ?? null }))
      .filter((c): c is { lat: number; lng: number } => c.lat !== null && c.lng !== null);
    if (coords.length === 0) return;
    if (coords.length === 1) {
      map.setCenter(coords[0]);
      map.setZoom(SINGLE_SCHOOL_ZOOM);
      return;
    }
    const bounds = new google.maps.LatLngBounds();
    coords.forEach((c) => bounds.extend(c));
    map.fitBounds(bounds, FIT_BOUNDS_PADDING);
  }, [map, boundsKey, schools]);
  return null;
}

const DEFAULT_TOGGLES: FilterToggles = {
  governmentAided: true,
  government: true,
  urban: true,
  rural: true,
  preschool: true,
  specialNeeds: true,
  both: true,
  none: true,
};

interface SchoolMapProps {
  initialSchools: School[];
}

export default function SchoolMap({ initialSchools }: SchoolMapProps) {
  const t = useTranslations("home");
  const searchParams = useSearchParams();
  const stateParam = searchParams.get("state");
  const [searchResult, setSearchResult] = useState<School | null>(null);

  // Filter state
  const [colourMode, setColourMode] = useState<ColourMode>("assistance");
  const [toggles, setToggles] = useState<FilterToggles>(DEFAULT_TOGGLES);
  const [enrolmentThreshold, setEnrolmentThreshold] = useState(30);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  // State-filtered subset: applied BEFORE the toggle filters so the
  // MapFilterPanel's "X of Y" count reflects the state context, not the
  // national total.
  const stateScopedSchools = useMemo(
    () => filterByStateParam(initialSchools, stateParam),
    [initialSchools, stateParam],
  );

  // Filter schools based on toggles and colour mode
  const filteredSchools = useMemo(() => {
    if (searchResult) return [searchResult];

    return stateScopedSchools.filter((school) => {
      switch (colourMode) {
        case "assistance": {
          const isAided = school.assistance_type === "SBK" || school.assistance_type === "SABK";
          if (isAided && !toggles.governmentAided) return false;
          if (!isAided && !toggles.government) return false;
          return true;
        }
        case "location": {
          const isUrban = school.location_type === "Bandar";
          if (isUrban && !toggles.urban) return false;
          if (!isUrban && !toggles.rural) return false;
          return true;
        }
        case "programmes": {
          const hasPreschool = (school.preschool_enrolment ?? 0) > 0;
          const hasSpecial = (school.special_enrolment ?? 0) > 0;
          if (hasPreschool && hasSpecial && !toggles.both) return false;
          if (hasPreschool && !hasSpecial && !toggles.preschool) return false;
          if (!hasPreschool && hasSpecial && !toggles.specialNeeds) return false;
          if (!hasPreschool && !hasSpecial && !toggles.none) return false;
          return true;
        }
        case "enrolment":
          return (school.enrolment ?? 0) <= enrolmentThreshold;
        default:
          return true;
      }
    });
  }, [stateScopedSchools, searchResult, colourMode, toggles, enrolmentThreshold]);

  const handleToggleChange = useCallback((key: keyof FilterToggles) => {
    setToggles((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleReset = useCallback(() => {
    setColourMode("assistance");
    setToggles(DEFAULT_TOGGLES);
    setEnrolmentThreshold(30);
    setSearchResult(null);
  }, []);

  const handleSearchSelect = useCallback((school: School) => {
    setSearchResult(school);
  }, []);

  const handleSearchClear = useCallback(() => {
    setSearchResult(null);
  }, []);

  if (!apiKey) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow text-center max-w-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            {t("apiKeyRequired")}
          </h2>
          <p className="text-sm text-gray-600">
            {t("apiKeyInstructions")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* State-filter chip — only renders when a ?state= URL param is active */}
      {stateParam && (
        <div className="absolute top-4 right-4 z-10 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 shadow-sm text-xs text-gray-700">
          <span className="font-medium">{stateParam}</span>
          <span className="text-gray-400">·</span>
          <span className="tabular-nums">{stateScopedSchools.length} {stateScopedSchools.length === 1 ? "school" : "schools"}</span>
          <Link
            href="/"
            className="text-blue-600 hover:text-blue-800"
            aria-label="Clear state filter"
          >
            ✕
          </Link>
        </div>
      )}

      {/* Controls overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-3 w-64 md:w-72">
        <SearchBox
          onSelect={handleSearchSelect}
          onClear={handleSearchClear}
        />
        <MapFilterPanel
          colourMode={colourMode}
          onColourModeChange={setColourMode}
          toggles={toggles}
          onToggleChange={handleToggleChange}
          enrolmentThreshold={enrolmentThreshold}
          onEnrolmentThresholdChange={setEnrolmentThreshold}
          onReset={handleReset}
          filteredCount={filteredSchools.length}
          totalCount={initialSchools.length}
        />
      </div>

      {/* Map */}
      <div className="map-container">
        <APIProvider apiKey={apiKey}>
          <Map
            defaultCenter={MALAYSIA_CENTER}
            defaultZoom={DEFAULT_ZOOM}
            mapId={mapId || undefined}
            gestureHandling="greedy"
            disableDefaultUI={false}
            mapTypeControl={false}
            streetViewControl={false}
          >
            <SchoolMarkers
              schools={filteredSchools}
              colourMode={colourMode}
              enrolmentThreshold={enrolmentThreshold}
            />
            <FitBoundsOnStateFilter
              schools={stateScopedSchools}
              boundsKey={stateParam ?? ""}
            />
          </Map>
        </APIProvider>
      </div>
    </div>
  );
}
