import "@testing-library/jest-dom";
import { filterByStateParam } from "@/components/SchoolMap";
import { School } from "@/lib/types";

// Minimal duck-typed school for filter testing.
const makeSchool = (
  moe_code: string,
  state: string,
  overrides: Partial<School> = {},
): School =>
  ({
    moe_code,
    state,
    name: `Sekolah Jenis Kebangsaan (Tamil) ${moe_code}`,
    short_name: `SJK(T) ${moe_code}`,
    enrolment: 100,
    gps_lat: 3.1,
    gps_lng: 101.7,
    ...overrides,
  } as School);

describe("filterByStateParam", () => {
  const schools = [
    makeSchool("J001", "Johor"),
    makeSchool("J002", "Johor"),
    makeSchool("P001", "Perak"),
    makeSchool("W001", "W.P. Kuala Lumpur"),
    makeSchool("S001", "Selangor"),
  ];

  it("returns all schools when stateParam is null", () => {
    expect(filterByStateParam(schools, null)).toHaveLength(5);
  });

  it("returns all schools when stateParam is empty string", () => {
    expect(filterByStateParam(schools, "")).toHaveLength(5);
  });

  it("filters to exact state match (case-sensitive value)", () => {
    const result = filterByStateParam(schools, "Johor");
    expect(result).toHaveLength(2);
    expect(result.every((s) => s.state === "Johor")).toBe(true);
  });

  it("is case-insensitive on the state name", () => {
    expect(filterByStateParam(schools, "JOHOR")).toHaveLength(2);
    expect(filterByStateParam(schools, "johor")).toHaveLength(2);
    expect(filterByStateParam(schools, "JoHoR")).toHaveLength(2);
  });

  it("trims surrounding whitespace from the param", () => {
    expect(filterByStateParam(schools, "  Perak  ")).toHaveLength(1);
  });

  it("matches the W.P. Kuala Lumpur canonical form", () => {
    const result = filterByStateParam(schools, "W.P. Kuala Lumpur");
    expect(result).toHaveLength(1);
    expect(result[0].moe_code).toBe("W001");
  });

  it("returns empty when no school matches", () => {
    expect(filterByStateParam(schools, "Atlantis")).toEqual([]);
  });

  it("returns empty when the school list is empty", () => {
    expect(filterByStateParam([], "Johor")).toEqual([]);
  });

  it("Sprint 26 #4: passes string-typed gps_lat/gps_lng through (FitBoundsOnStateFilter coerces)", () => {
    // DRF serialises DecimalField as string. The pure filter doesn't
    // care about coord types — the regression was downstream in
    // FitBoundsOnStateFilter where bounds.extend({lat:"3.1"}) crashed.
    // Smoke test that filter returns the same row shape it received.
    const stringCoords = [
      makeSchool("J001", "Johor", {
        gps_lat: "1.4854" as unknown as number,
        gps_lng: "103.7611" as unknown as number,
      }),
    ];
    const out = filterByStateParam(stringCoords, "Johor");
    expect(out).toHaveLength(1);
    expect(typeof out[0].gps_lat).toBe("string");
  });
});
