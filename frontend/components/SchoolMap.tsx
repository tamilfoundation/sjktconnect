"use client";

import { useCallback, useEffect, useState } from "react";
import { APIProvider, Map } from "@vis.gl/react-google-maps";
import SchoolMarkers from "./SchoolMarkers";
import StateFilter from "./StateFilter";
import SearchBox from "./SearchBox";
import { fetchAllSchools, getUniqueStates } from "@/lib/api";
import { School } from "@/lib/types";

const MALAYSIA_CENTER = { lat: 4.2105, lng: 101.9758 };
const DEFAULT_ZOOM = 7;

export default function SchoolMap() {
  const [allSchools, setAllSchools] = useState<School[]>([]);
  const [filteredSchools, setFilteredSchools] = useState<School[]>([]);
  const [states, setStates] = useState<string[]>([]);
  const [selectedState, setSelectedState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  // Load all schools on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAllSchools()
      .then((schools) => {
        if (cancelled) return;
        // Only include schools with GPS coordinates
        const withGps = schools.filter((s) => s.gps_lat && s.gps_lng);
        setAllSchools(withGps);
        setFilteredSchools(withGps);
        setStates(getUniqueStates(withGps));
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Filter by state
  const handleStateChange = useCallback(
    (state: string) => {
      setSelectedState(state);
      if (!state) {
        setFilteredSchools(allSchools);
      } else {
        setFilteredSchools(allSchools.filter((s) => s.state === state));
      }
    },
    [allSchools]
  );

  // Search result selection — highlight on map
  const handleSearchSelect = useCallback(
    (school: School) => {
      // Clear state filter and show just this school
      setSelectedState("");
      setFilteredSchools([school]);
    },
    []
  );

  const handleSearchClear = useCallback(() => {
    setSelectedState("");
    setFilteredSchools(allSchools);
  }, [allSchools]);

  if (!apiKey) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow text-center max-w-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            Google Maps API Key Required
          </h2>
          <p className="text-sm text-gray-600">
            Set <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> in
            your <code className="bg-gray-100 px-1 rounded">.env.local</code> file.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Controls overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-3 w-72">
        <SearchBox
          onSelect={handleSearchSelect}
          onClear={handleSearchClear}
        />
        <StateFilter
          states={states}
          selectedState={selectedState}
          onChange={handleStateChange}
          schoolCount={filteredSchools.length}
          totalCount={allSchools.length}
        />
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/80">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600 mx-auto mb-3" />
            <p className="text-sm text-gray-600">Loading 528 schools...</p>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/80">
          <div className="bg-white p-6 rounded-lg shadow text-center max-w-md">
            <h2 className="text-lg font-semibold text-red-700 mb-2">
              Failed to load schools
            </h2>
            <p className="text-sm text-gray-600 mb-4">{error}</p>
            <button
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700"
              onClick={() => window.location.reload()}
            >
              Retry
            </button>
          </div>
        </div>
      )}

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
            <SchoolMarkers schools={filteredSchools} />
          </Map>
        </APIProvider>
      </div>
    </div>
  );
}
