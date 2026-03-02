"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { APIProvider, Map, useMap } from "@vis.gl/react-google-maps";
import { GeoJSONFeature } from "@/lib/types";

interface BoundaryMapProps {
  geoJSON: GeoJSONFeature | null;
  center: { lat: number; lng: number };
  zoom?: number;
}

function BoundaryLayer({ geoJSON }: { geoJSON: GeoJSONFeature }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !geoJSON) return;

    // Add GeoJSON data to the map
    map.data.addGeoJson(geoJSON);

    // Style the boundary
    map.data.setStyle({
      fillColor: "#6366f1",
      fillOpacity: 0.15,
      strokeColor: "#4f46e5",
      strokeWeight: 2,
    });

    return () => {
      // Clean up on unmount
      map.data.forEach((feature) => {
        map.data.remove(feature);
      });
    };
  }, [map, geoJSON]);

  return null;
}

export default function BoundaryMap({
  geoJSON,
  center,
  zoom = 11,
}: BoundaryMapProps) {
  const tc = useTranslations("common");
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  if (!apiKey) {
    return (
      <div className="w-full h-72 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 text-sm">
        {tc("mapUnavailable")}
      </div>
    );
  }

  if (!geoJSON) {
    return (
      <div className="w-full h-72 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 text-sm">
        {tc("noBoundaryData")}
      </div>
    );
  }

  return (
    <div className="w-full h-72 rounded-lg overflow-hidden border border-gray-200">
      <APIProvider apiKey={apiKey}>
        <Map
          defaultCenter={center}
          defaultZoom={zoom}
          mapId={mapId || undefined}
          disableDefaultUI={true}
          zoomControl={true}
        >
          <BoundaryLayer geoJSON={geoJSON} />
        </Map>
      </APIProvider>
    </div>
  );
}
