"use client";

import { APIProvider, Map, AdvancedMarker, Pin } from "@vis.gl/react-google-maps";

interface MiniMapProps {
  lat: number;
  lng: number;
  schoolName: string;
}

export default function MiniMap({ lat, lng, schoolName }: MiniMapProps) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "";

  if (!apiKey) {
    return (
      <div className="w-full h-64 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 text-sm">
        Map unavailable
      </div>
    );
  }

  return (
    <div className="w-full h-64 rounded-lg overflow-hidden border border-gray-200">
      <APIProvider apiKey={apiKey}>
        <Map
          defaultCenter={{ lat: Number(lat), lng: Number(lng) }}
          defaultZoom={15}
          mapId={mapId || undefined}
          disableDefaultUI={true}
          zoomControl={true}
        >
          <AdvancedMarker position={{ lat: Number(lat), lng: Number(lng) }} title={schoolName}>
            <Pin background="#4f46e5" glyphColor="#fff" borderColor="#3730a3" />
          </AdvancedMarker>
        </Map>
      </APIProvider>
    </div>
  );
}
