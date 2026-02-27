import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import SchoolTable from "@/components/SchoolTable";
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

describe("SchoolTable", () => {
  it("shows empty message when no schools", () => {
    render(<SchoolTable schools={[]} />);
    expect(screen.getByText(/No Tamil schools found/)).toBeInTheDocument();
  });

  it("renders school count in heading", () => {
    render(<SchoolTable schools={[makeSchool()]} />);
    expect(screen.getByText("Tamil Schools (1)")).toBeInTheDocument();
  });

  it("renders table headers", () => {
    render(<SchoolTable schools={[makeSchool()]} />);
    expect(screen.getByText("School")).toBeInTheDocument();
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("PPD")).toBeInTheDocument();
  });

  it("renders school name as link", () => {
    render(<SchoolTable schools={[makeSchool()]} />);
    const link = screen.getByText("SJK(T) Ladang Bikam").closest("a");
    expect(link).toHaveAttribute("href", "/school/JBD0050");
  });

  it("renders enrolment and teacher count", () => {
    render(<SchoolTable schools={[makeSchool()]} />);
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
  });

  it("renders MOE code", () => {
    render(<SchoolTable schools={[makeSchool()]} />);
    expect(screen.getByText("JBD0050")).toBeInTheDocument();
  });

  it("renders multiple schools", () => {
    const schools = [
      makeSchool({ moe_code: "A001", short_name: "School A" }),
      makeSchool({ moe_code: "A002", short_name: "School B" }),
    ];
    render(<SchoolTable schools={schools} />);
    expect(screen.getByText("Tamil Schools (2)")).toBeInTheDocument();
    expect(screen.getByText("School A")).toBeInTheDocument();
    expect(screen.getByText("School B")).toBeInTheDocument();
  });
});
