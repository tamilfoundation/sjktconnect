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

function getAssistanceLabel(type: string): string {
  return type === "SBK" || type === "SABK" ? "governmentAided" : "government";
}

function getLocationLabel(type: string): string {
  return type === "Bandar" ? "urban" : "rural";
}

function getRatio(enrolment: number, teachers: number): string {
  if (!teachers) return "—";
  const ratio = Math.round(enrolment / teachers);
  return `${ratio}:1`;
}

export default function SchoolMarkers({
  schools,
  colourMode,
  enrolmentThreshold,
}: SchoolMarkersProps) {
  const t = useTranslations("mapInfoWindow");
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
          <div style={{ width: 280 }}>
            {/* School image or placeholder */}
            {selectedSchool.image_url ? (
              <img
                src={selectedSchool.image_url}
                alt={selectedSchool.short_name || selectedSchool.name}
                style={{
                  width: "100%",
                  height: 130,
                  objectFit: "cover",
                  borderRadius: "8px 8px 0 0",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  height: 130,
                  background: "linear-gradient(135deg, #e0e7ff, #c7d2fe)",
                  borderRadius: "8px 8px 0 0",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#6366f1",
                  fontSize: 36,
                }}
              >
                🏫
              </div>
            )}

            {/* Content */}
            <div style={{ padding: "10px 12px 12px" }}>
              {/* School name */}
              <h3 style={{ margin: "0 0 6px", fontSize: 15, fontWeight: 700, color: "#1e293b", lineHeight: 1.3 }}>
                {selectedSchool.short_name || selectedSchool.name}
              </h3>

              {/* Badges */}
              <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#fff",
                    background: selectedSchool.assistance_type === "SBK" || selectedSchool.assistance_type === "SABK"
                      ? "#7c3aed" : "#ea580c",
                  }}
                >
                  {t(getAssistanceLabel(selectedSchool.assistance_type))}
                </span>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#fff",
                    background: selectedSchool.location_type === "Bandar" ? "#2563eb" : "#16a34a",
                  }}
                >
                  {t(getLocationLabel(selectedSchool.location_type))}
                </span>
              </div>

              {/* Stats row */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-around",
                  padding: "8px 0",
                  borderTop: "1px solid #e2e8f0",
                  borderBottom: "1px solid #e2e8f0",
                  marginBottom: 8,
                }}
              >
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
                    {selectedSchool.enrolment?.toLocaleString() ?? "—"}
                  </div>
                  <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
                    {t("students")}
                  </div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
                    {selectedSchool.teacher_count || "—"}
                  </div>
                  <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
                    {t("teachers")}
                  </div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#1e293b" }}>
                    {getRatio(selectedSchool.enrolment ?? 0, selectedSchool.teacher_count)}
                  </div>
                  <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
                    {t("ratio")}
                  </div>
                </div>
              </div>

              {/* Constituency & DUN links */}
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 10, lineHeight: 1.6 }}>
                {selectedSchool.constituency_code && (
                  <div>
                    <Link
                      href={`/constituency/${selectedSchool.constituency_code}`}
                      style={{ color: "#4f46e5", textDecoration: "none", fontWeight: 500 }}
                    >
                      {selectedSchool.constituency_code} {selectedSchool.constituency_name}
                    </Link>
                  </div>
                )}
                {selectedSchool.dun_id && (
                  <div>
                    <Link
                      href={`/dun/${selectedSchool.dun_id}`}
                      style={{ color: "#4f46e5", textDecoration: "none", fontWeight: 500 }}
                    >
                      {selectedSchool.dun_code} {selectedSchool.dun_name}
                    </Link>
                  </div>
                )}
              </div>

              {/* View School button */}
              <Link
                href={`/school/${selectedSchool.moe_code}`}
                style={{
                  display: "block",
                  textAlign: "center",
                  padding: "8px 0",
                  background: "#4f46e5",
                  color: "#fff",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                {t("viewSchool")}
              </Link>
            </div>
          </div>
        </InfoWindow>
      )}
    </>
  );
}
