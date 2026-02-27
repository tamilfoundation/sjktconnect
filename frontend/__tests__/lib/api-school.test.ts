import {
  fetchSchoolDetail,
  fetchSchoolsByConstituency,
  fetchSchoolMentions,
} from "@/lib/api";
import { SchoolDetail, SchoolMention } from "@/lib/types";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

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
  name_tamil: "",
  address: "Ladang Bikam",
  postcode: "85000",
  city: "Segamat",
  email: "JBD0050@moe.edu.my",
  phone: "07-1234567",
  fax: "",
  gps_verified: true,
  preschool_enrolment: 0,
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

const makeMention = (
  overrides: Partial<SchoolMention> = {}
): SchoolMention => ({
  sitting_date: "2026-02-01",
  mp_name: "YB Test MP",
  mp_constituency: "Segamat",
  mp_party: "BN",
  mention_type: "question",
  significance: 3,
  sentiment: "positive",
  ai_summary: "MP asked about school facilities",
  verbatim_quote: "SJK(T) Ladang Bikam memerlukan...",
  ...overrides,
});

describe("fetchSchoolDetail", () => {
  it("fetches a school by MOE code", async () => {
    const school = makeSchoolDetail();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => school,
    });

    const result = await fetchSchoolDetail("JBD0050");
    expect(result.moe_code).toBe("JBD0050");
    expect(result.grade).toBe("A");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/schools/JBD0050/")
    );
  });

  it("throws on 404", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });

    await expect(fetchSchoolDetail("INVALID")).rejects.toThrow(
      "API error: 404"
    );
  });
});

describe("fetchSchoolsByConstituency", () => {
  it("fetches schools for a constituency", async () => {
    const school = makeSchoolDetail();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        count: 1,
        next: null,
        previous: null,
        results: [school],
      }),
    });

    const result = await fetchSchoolsByConstituency("P140");
    expect(result).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("constituency=P140")
    );
  });
});

describe("fetchSchoolMentions", () => {
  it("fetches mentions for a school", async () => {
    const mention = makeMention();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [mention],
    });

    const result = await fetchSchoolMentions("JBD0050");
    expect(result).toHaveLength(1);
    expect(result[0].mp_name).toBe("YB Test MP");
  });

  it("returns empty array on API error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });

    const result = await fetchSchoolMentions("JBD0050");
    expect(result).toEqual([]);
  });
});
