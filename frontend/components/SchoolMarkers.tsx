"use client";

import { useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { AdvancedMarker, InfoWindow, Pin } from "@vis.gl/react-google-maps";
import { Link } from "@/i18n/navigation";
import { School } from "@/lib/types";

interface SchoolMarkersProps {
  schools: School[];
}

export default function SchoolMarkers({ schools }: SchoolMarkersProps) {
  const t = useTranslations("home");
  const tc = useTranslations("common");
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);

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
          position={{ lat: Number(school.gps_lat), lng: Number(school.gps_lng) }}
          title={school.short_name || school.name}
          onClick={() => setSelectedSchool(school)}
        >
          <Pin background="#4f46e5" glyphColor="#fff" borderColor="#3730a3" />
        </AdvancedMarker>
      ))}

      {selectedSchool && (
        <InfoWindow
          position={{
            lat: Number(selectedSchool.gps_lat),
            lng: Number(selectedSchool.gps_lng),
          }}
          onCloseClick={handleClose}
        >
          <div className="info-window" style={{ maxWidth: 260 }}>
            <h3>{selectedSchool.short_name || selectedSchool.name}</h3>
            <p>
              <strong>{t("code")}</strong> {selectedSchool.moe_code}
            </p>
            <p>
              <strong>{t("state")}</strong> {selectedSchool.state}
            </p>
            <p>
              <strong>{t("enrolment")}</strong>{" "}
              {selectedSchool.enrolment?.toLocaleString() ?? tc("na")}
            </p>
            {selectedSchool.teacher_count > 0 && (
              <p>
                <strong>{t("teachers")}</strong> {selectedSchool.teacher_count}
              </p>
            )}
            {selectedSchool.constituency_name && (
              <p>
                <strong>{t("constituencyLabel")}</strong>{" "}
                {selectedSchool.constituency_name} (
                {selectedSchool.constituency_code})
              </p>
            )}
            <Link
              href={`/school/${selectedSchool.moe_code}`}
              style={{
                display: "inline-block",
                marginTop: 8,
                color: "#4f46e5",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              {t("viewSchool")}
            </Link>
          </div>
        </InfoWindow>
      )}
    </>
  );
}
