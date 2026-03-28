"use client";

import { useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { APIProvider, Map } from "@vis.gl/react-google-maps";
import SchoolMarkers from "./SchoolMarkers";
import MapFilterPanel, {
  ColourMode,
  FilterToggles,
} from "./MapFilterPanel";
import SearchBox from "./SearchBox";
import { School } from "@/lib/types";

const MALAYSIA_CENTER = { lat: 4.2105, lng: 101.9758 };
const DEFAULT_ZOOM = 7;

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
  const [searchResult, setSearchResult] = useState<School | null>(null);

  // Filter state
  const [colourMode, setColourMode] = useState<ColourMode>("assistance");
  const [toggles, setToggles] = useState<FilterToggles>(DEFAULT_TOGGLES);
  const [enrolmentThreshold, setEnrolmentThreshold] = useState(30);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  // Filter schools based on toggles and colour mode
  const filteredSchools = useMemo(() => {
    if (searchResult) return [searchResult];

    return initialSchools.filter((school) => {
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
  }, [initialSchools, searchResult, colourMode, toggles, enrolmentThreshold]);

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
          </Map>
        </APIProvider>
      </div>
    </div>
  );
}
