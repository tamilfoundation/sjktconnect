"use client";

import { useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { AdvancedMarker, InfoWindow, Pin } from "@vis.gl/react-google-maps";
import { Link } from "@/i18n/navigation";
import { School } from "@/lib/types";
import { ColourMode } from "./MapFilterPanel";

interface SchoolMarkersProps {
  schools: School[];
  colourMode: ColourMode;
  enrolmentThreshold: number;
}

function getPinColour(
  school: School,
  colourMode: ColourMode,
  enrolmentThreshold: number
): { background: string; border: string } {
  switch (colourMode) {
    case "assistance":
      if (school.assistance_type === "SBK" || school.assistance_type === "SABK") {
        return { background: "#7c3aed", border: "#6d28d9" }; // purple
      }
      return { background: "#ea580c", border: "#c2410c" }; // orange
    case "location":
      if (school.location_type === "Bandar") {
        return { background: "#2563eb", border: "#1d4ed8" }; // blue
      }
      return { background: "#16a34a", border: "#15803d" }; // green
    case "programmes": {
      const hasPreschool = (school.preschool_enrolment ?? 0) > 0;
      const hasSpecial = (school.special_enrolment ?? 0) > 0;
      if (hasPreschool && hasSpecial) {
        return { background: "#ea580c", border: "#c2410c" }; // orange
      }
      if (hasPreschool) {
        return { background: "#7c3aed", border: "#6d28d9" }; // purple
      }
      if (hasSpecial) {
        return { background: "#2563eb", border: "#1d4ed8" }; // blue
      }
      return { background: "#6b7280", border: "#4b5563" }; // grey
    }
    case "enrolment":
      return { background: "#dc2626", border: "#b91c1c" }; // red (filtered to threshold)
    default:
      return { background: "#4f46e5", border: "#3730a3" }; // indigo default
  }
}

export default function SchoolMarkers({
  schools,
  colourMode,
  enrolmentThreshold,
}: SchoolMarkersProps) {
  const t = useTranslations("home");
  const tc = useTranslations("common");
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);

  const handleClose = useCallback(() => setSelectedSchool(null), []);

  const visibleSchools = useMemo(
    () => schools.filter((s) => s.gps_lat !== null && s.gps_lng !== null),
    [schools]
  );

  return (
    <>
      {visibleSchools.map((school) => {
        const colours = getPinColour(school, colourMode, enrolmentThreshold);
        return (
          <AdvancedMarker
            key={school.moe_code}
            position={{ lat: Number(school.gps_lat), lng: Number(school.gps_lng) }}
            title={school.short_name || school.name}
            onClick={() => setSelectedSchool(school)}
          >
            <Pin
              background={colours.background}
              glyphColor="#fff"
              borderColor={colours.border}
            />
          </AdvancedMarker>
        );
      })}

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
