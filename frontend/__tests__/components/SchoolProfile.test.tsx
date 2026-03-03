import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import SchoolProfile from "@/components/SchoolProfile";
import { SchoolDetail } from "@/lib/types";

const makeSchoolDetail = (
  overrides: Partial<SchoolDetail> = {}
): SchoolDetail => ({
  moe_code: "JBD0050",
  name: "Sekolah Jenis Kebangsaan (Tamil) Ladang Bikam",
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
  assistance_type: "SBK",
  session_count: 1,
  session_type: "Pagi",
  skm_eligible: false,
  location_type: "Luar Bandar",
  dun_code: "N01",
  dun_name: "Buloh Kasap",
  last_verified: null,
  image_url: null,
  images: [],
  leaders: [],
  ...overrides,
});

describe("SchoolProfile", () => {
  it("renders school details section", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.getByText("School Details")).toBeInTheDocument();
  });

  it("renders Tamil name when present", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(
      screen.getByText("எஸ்.ஜே.கே.(த) லாடாங் பிகாம்")
    ).toBeInTheDocument();
  });

  it("renders address with postcode and city grouped", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(
      screen.getByText(/Ladang Bikam, Segamat, 85000 Segamat, Johor/)
    ).toBeInTheDocument();
  });

  it("renders political representation", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.getByText("Political Representation")).toBeInTheDocument();
    expect(screen.getByText(/P140 Segamat/)).toBeInTheDocument();
    expect(screen.getByText(/N01 Buloh Kasap/)).toBeInTheDocument();
  });

  it("always shows enrolment breakdown rows", () => {
    render(
      <SchoolProfile
        school={makeSchoolDetail({
          enrolment: 120,
          preschool_enrolment: 15,
          special_enrolment: 3,
        })}
      />
    );
    expect(screen.getByText("School")).toBeInTheDocument();
    expect(screen.getByText("120 students")).toBeInTheDocument();
    expect(screen.getByText("Preschool")).toBeInTheDocument();
    expect(screen.getByText("15 students")).toBeInTheDocument();
    expect(screen.getByText("Special Needs")).toBeInTheDocument();
    expect(screen.getByText("3 students")).toBeInTheDocument();
  });

  it("hides zero-enrolment breakdown rows", () => {
    render(
      <SchoolProfile
        school={makeSchoolDetail({
          enrolment: 50,
          preschool_enrolment: 0,
          special_enrolment: 0,
        })}
      />
    );
    expect(screen.getByText("School")).toBeInTheDocument();
    expect(screen.getByText("50 students")).toBeInTheDocument();
    expect(screen.queryByText("Preschool")).not.toBeInTheDocument();
    expect(screen.queryByText("Special Needs")).not.toBeInTheDocument();
  });

  it("does not render SKM stat card", () => {
    render(
      <SchoolProfile school={makeSchoolDetail({ skm_eligible: true })} />
    );
    expect(screen.queryByText("SKM")).not.toBeInTheDocument();
    expect(screen.queryByText("Eligible")).not.toBeInTheDocument();
  });

  it("does not render MOE Code detail row", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.queryByText("MOE Code")).not.toBeInTheDocument();
  });

  it("does not render Full Name detail row", () => {
    render(<SchoolProfile school={makeSchoolDetail()} />);
    expect(screen.queryByText("Full Name")).not.toBeInTheDocument();
  });

  it("maps SBK assistance type to Fully Government-Aided", () => {
    render(
      <SchoolProfile school={makeSchoolDetail({ assistance_type: "SBK" })} />
    );
    expect(screen.getByText("Fully Government-Aided")).toBeInTheDocument();
  });

  it("maps SK assistance type to Government School", () => {
    render(
      <SchoolProfile school={makeSchoolDetail({ assistance_type: "SK" })} />
    );
    expect(screen.getByText("Government School")).toBeInTheDocument();
  });

  it("renders school leadership section when leaders exist", () => {
    render(
      <SchoolProfile
        school={makeSchoolDetail({
          leaders: [
            {
              role: "CHAIRMAN",
              role_display: "Board Chairman",
              name: "Mr. Rajan",
            },
            {
              role: "HEADMASTER",
              role_display: "Headmaster",
              name: "Mrs. Devi",
            },
          ],
        })}
      />
    );
    expect(screen.getByText("School Leadership")).toBeInTheDocument();
    expect(screen.getByText("Board Chairman")).toBeInTheDocument();
    expect(screen.getByText("Mr. Rajan")).toBeInTheDocument();
    expect(screen.getByText("Headmaster")).toBeInTheDocument();
    expect(screen.getByText("Mrs. Devi")).toBeInTheDocument();
  });

  it("hides school leadership section when no leaders", () => {
    render(<SchoolProfile school={makeSchoolDetail({ leaders: [] })} />);
    expect(screen.queryByText("School Leadership")).not.toBeInTheDocument();
  });
});
