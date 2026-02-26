"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AdvancedMarker,
  InfoWindow,
  useMap,
} from "@vis.gl/react-google-maps";
import { MarkerClusterer } from "@googlemaps/markerclusterer";
import type { Marker } from "@googlemaps/markerclusterer";
import { School } from "@/lib/types";

interface SchoolMarkersProps {
  schools: School[];
}

export default function SchoolMarkers({ schools }: SchoolMarkersProps) {
  const map = useMap();
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const clusterer = useRef<MarkerClusterer | null>(null);
  const markersRef = useRef<Map<string, Marker>>(new Map());

  // Initialise clusterer when map is ready
  useEffect(() => {
    if (!map) return;
    if (!clusterer.current) {
      clusterer.current = new MarkerClusterer({ map, markers: [] });
    }
  }, [map]);

  // Update clusterer markers when schools change
  useEffect(() => {
    if (!clusterer.current) return;
    clusterer.current.clearMarkers();
    const currentMarkers = Array.from(markersRef.current.values());
    clusterer.current.addMarkers(currentMarkers);
  }, [schools]);

  // Track marker refs for clustering
  const setMarkerRef = useCallback(
    (marker: Marker | null, key: string) => {
      if (marker) {
        markersRef.current.set(key, marker);
      } else {
        markersRef.current.delete(key);
      }
    },
    []
  );

  // Close info window
  const handleClose = useCallback(() => setSelectedSchool(null), []);

  // Memoize visible schools with valid GPS
  const visibleSchools = useMemo(
    () => schools.filter((s) => s.gps_lat !== null && s.gps_lng !== null),
    [schools]
  );

  return (
    <>
      {visibleSchools.map((school) => (
        <AdvancedMarker
          key={school.moe_code}
          position={{ lat: school.gps_lat!, lng: school.gps_lng! }}
          ref={(marker) => setMarkerRef(marker, school.moe_code)}
          onClick={() => setSelectedSchool(school)}
        />
      ))}

      {selectedSchool && (
        <InfoWindow
          position={{
            lat: selectedSchool.gps_lat!,
            lng: selectedSchool.gps_lng!,
          }}
          onCloseClick={handleClose}
        >
          <div className="info-window" style={{ maxWidth: 260 }}>
            <h3>{selectedSchool.short_name || selectedSchool.name}</h3>
            <p>
              <strong>Code:</strong> {selectedSchool.moe_code}
            </p>
            <p>
              <strong>State:</strong> {selectedSchool.state}
            </p>
            <p>
              <strong>Enrolment:</strong>{" "}
              {selectedSchool.enrolment?.toLocaleString() ?? "N/A"}
            </p>
            {selectedSchool.teacher_count > 0 && (
              <p>
                <strong>Teachers:</strong> {selectedSchool.teacher_count}
              </p>
            )}
            {selectedSchool.constituency_name && (
              <p>
                <strong>Constituency:</strong>{" "}
                {selectedSchool.constituency_name} (
                {selectedSchool.constituency_code})
              </p>
            )}
          </div>
        </InfoWindow>
      )}
    </>
  );
}
