import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import SchoolProfile from "@/components/SchoolProfile";
import { SchoolDetail } from "@/lib/types";

const makeSchoolDetail = (
  overrides: Partial<SchoolDetail> = {}
): SchoolDetail => ({
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
  name_tamil: "எஸ்.ஜே.கே.(த) லாடாங் பிகாம்",
  address: "Ladang Bikam, Segamat",
  postcode: "85000",
  city: "Segamat",
  email: "JBD0050@moe.edu.my",
  phone: "07-1234567",
  fax: "",
  gps_verified: true,
  preschool_enrolment: 15,
  special_enrolment: 0,
  grade: "A",
  assistance_type: "Bantuan Penuh",
  session_count: 1,
  session_type: "Pagi",
  skm_eligible: false,
  location_type: "Luar Bandar",
  dun_code: "N01",
  dun_name: "Buloh Kasap",
  last_verified: null,
  ...overrides,
});

describe("SchoolProfile", () => {
  it("renders stat cards with key data", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("Teachers")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Grade")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("renders school details section", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.getByText("School Details")).toBeInTheDocument();
    expect(screen.getByText("JBD0050")).toBeInTheDocument();
  });

  it("renders Tamil name when present", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(
      screen.getByText("எஸ்.ஜே.கே.(த) லாடாங் பிகாம்")
    ).toBeInTheDocument();
  });

  it("renders address", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(
      screen.getByText(/Ladang Bikam, Segamat.*85000/)
    ).toBeInTheDocument();
  });

  it("renders political representation", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.getByText("Political Representation")).toBeInTheDocument();
    expect(screen.getByText(/P140 Segamat/)).toBeInTheDocument();
    expect(screen.getByText(/N01 Buloh Kasap/)).toBeInTheDocument();
  });

  it("renders preschool enrolment when > 0", () => {
    render(
      <SchoolProfile school={makeSchoolDetail({ preschool_enrolment: 15 })} />
    );
    expect(screen.getByText("15 students")).toBeInTheDocument();
  });

  it("hides preschool when 0", () => {
    render(
      <SchoolProfile school={makeSchoolDetail({ preschool_enrolment: 0 })} />
    );
    expect(screen.queryByText("Preschool")).not.toBeInTheDocument();
  });

  it("shows SKM as Eligible or No", () => {
    const { rerender } = render(
      <SchoolProfile school={makeSchoolDetail({ skm_eligible: true })} />
    );
    expect(screen.getByText("Eligible")).toBeInTheDocument();

    rerender(
      <SchoolProfile school={makeSchoolDetail({ skm_eligible: false })} />
    );
    expect(screen.getByText("No")).toBeInTheDocument();
  });
});
