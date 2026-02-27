import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ConstituencySchools from "@/components/ConstituencySchools";
import { School } from "@/lib/types";

const makeSchool = (overrides: Partial<School> = {}): School => ({
  moe_code: "JBD0050",
  name: "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
  short_name: "SJK(T) Ladang Bikam",
  state: "Johor",
  ppd: "PPD Segamat",
  constituency_code: "P140",
  constituency_name: "Segamat",
  enrolment: 120,
  teacher_count: 8,
  gps_lat: 2.5,
  gps_lng: 102.8,
  is_active: true,
  ...overrides,
});

describe("ConstituencySchools", () => {
  it("returns null when no other schools", () => {
    const { container } = render(
      <ConstituencySchools
        schools={[makeSchool()]}
        currentMoeCode="JBD0050"
        constituencyName="Segamat"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders other schools in the constituency", () => {
    const schools = [
      makeSchool({ moe_code: "JBD0050", short_name: "SJK(T) Bikam" }),
      makeSchool({ moe_code: "JBD0051", short_name: "SJK(T) Tenang" }),
      makeSchool({ moe_code: "JBD0052", short_name: "SJK(T) Jabi" }),
    ];

    render(
      <ConstituencySchools
        schools={schools}
        currentMoeCode="JBD0050"
        constituencyName="Segamat"
      />
    );

    expect(screen.getByText("Schools in Segamat")).toBeInTheDocument();
    expect(screen.getByText("SJK(T) Tenang")).toBeInTheDocument();
    expect(screen.getByText("SJK(T) Jabi")).toBeInTheDocument();
    // Current school should be excluded
    expect(screen.queryByText("SJK(T) Bikam")).not.toBeInTheDocument();
  });

  it("renders school links with correct hrefs", () => {
    const schools = [
      makeSchool({ moe_code: "JBD0050" }),
      makeSchool({ moe_code: "JBD0051", short_name: "SJK(T) Tenang" }),
    ];

    render(
      <ConstituencySchools
        schools={schools}
        currentMoeCode="JBD0050"
        constituencyName="Segamat"
      />
    );

    const link = screen.getByText("SJK(T) Tenang").closest("a");
    expect(link).toHaveAttribute("href", "/school/JBD0051");
  });

  it("shows enrolment for each school", () => {
    const schools = [
      makeSchool({ moe_code: "JBD0050" }),
      makeSchool({ moe_code: "JBD0051", enrolment: 250 }),
    ];

    render(
      <ConstituencySchools
        schools={schools}
        currentMoeCode="JBD0050"
        constituencyName="Segamat"
      />
    );

    expect(screen.getByText("250 students")).toBeInTheDocument();
  });
});
