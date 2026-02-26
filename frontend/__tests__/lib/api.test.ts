import { fetchAllSchools, searchEntities, getUniqueStates } from "@/lib/api";
import { School } from "@/lib/types";

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

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

describe("fetchAllSchools", () => {
  it("fetches a single page when next is null", async () => {
    const school = makeSchool();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        count: 1,
        next: null,
        previous: null,
        results: [school],
      }),
    });

    const result = await fetchAllSchools();
    expect(result).toHaveLength(1);
    expect(result[0].moe_code).toBe("JBD0050");
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("fetches multiple pages", async () => {
    const school1 = makeSchool({ moe_code: "A001" });
    const school2 = makeSchool({ moe_code: "A002" });

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          count: 2,
          next: "http://localhost:8000/api/v1/schools/?page=2",
          previous: null,
          results: [school1],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          count: 2,
          next: null,
          previous: "http://localhost:8000/api/v1/schools/",
          results: [school2],
        }),
      });

    const result = await fetchAllSchools();
    expect(result).toHaveLength(2);
    expect(result[0].moe_code).toBe("A001");
    expect(result[1].moe_code).toBe("A002");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("passes state filter to URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        count: 0,
        next: null,
        previous: null,
        results: [],
      }),
    });

    await fetchAllSchools("Johor");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("state=Johor")
    );
  });

  it("throws on API error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    await expect(fetchAllSchools()).rejects.toThrow("API error: 500");
  });
});

describe("searchEntities", () => {
  it("returns empty results for short queries", async () => {
    const result = await searchEntities("a");
    expect(result).toEqual({ schools: [], constituencies: [] });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("calls search API for valid queries", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        schools: [makeSchool()],
        constituencies: [],
      }),
    });

    const result = await searchEntities("bikam");
    expect(result.schools).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("search/?q=bikam")
    );
  });
});

describe("getUniqueStates", () => {
  it("returns sorted unique states", () => {
    const schools = [
      makeSchool({ state: "Selangor" }),
      makeSchool({ state: "Johor" }),
      makeSchool({ state: "Selangor" }),
      makeSchool({ state: "Perak" }),
    ];
    expect(getUniqueStates(schools)).toEqual(["Johor", "Perak", "Selangor"]);
  });

  it("returns empty array for empty input", () => {
    expect(getUniqueStates([])).toEqual([]);
  });
});
