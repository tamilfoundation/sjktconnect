import {
  fetchConstituencies,
  fetchConstituencyDetail,
  fetchConstituencyGeoJSON,
  fetchDUNs,
  fetchDUNDetail,
  fetchDUNGeoJSON,
} from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

describe("fetchConstituencies", () => {
  it("fetches all constituencies", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            code: "P140",
            name: "Segamat",
            state: "Johor",
            mp_name: "Test MP",
            mp_party: "BN",
            school_count: 5,
          },
        ],
      }),
    });

    const result = await fetchConstituencies();
    expect(result).toHaveLength(1);
    expect(result[0].code).toBe("P140");
  });

  it("passes state filter", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 0, next: null, previous: null, results: [] }),
    });

    await fetchConstituencies("Johor");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("state=Johor")
    );
  });

  it("paginates through multiple pages", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          count: 2,
          next: "http://localhost:8000/api/v1/constituencies/?page=2",
          previous: null,
          results: [{ code: "P001", name: "A", state: "Johor", mp_name: "", mp_party: "", school_count: 1 }],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          count: 2,
          next: null,
          previous: null,
          results: [{ code: "P002", name: "B", state: "Johor", mp_name: "", mp_party: "", school_count: 2 }],
        }),
      });

    const result = await fetchConstituencies();
    expect(result).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});

describe("fetchConstituencyDetail", () => {
  it("fetches detail by code", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        code: "P140",
        name: "Segamat",
        state: "Johor",
        mp_name: "Test MP",
        mp_party: "BN",
        mp_coalition: "BN",
        schools: [],
        scorecard: null,
        indian_population: 5000,
        indian_percentage: 10.5,
        avg_income: 3500,
        poverty_rate: 2.1,
        gini: 0.35,
        unemployment_rate: 3.2,
      }),
    });

    const result = await fetchConstituencyDetail("P140");
    expect(result.code).toBe("P140");
    expect(result.indian_population).toBe(5000);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/constituencies/P140/")
    );
  });
});

describe("fetchConstituencyGeoJSON", () => {
  it("returns geojson on success", async () => {
    const feature = {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [[[0, 0]]] },
      properties: { code: "P140" },
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => feature,
    });

    const result = await fetchConstituencyGeoJSON("P140");
    expect(result).toEqual(feature);
  });

  it("returns null on error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });

    const result = await fetchConstituencyGeoJSON("INVALID");
    expect(result).toBeNull();
  });
});

describe("fetchDUNs", () => {
  it("fetches DUNs with constituency filter", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        count: 1,
        next: null,
        previous: null,
        results: [
          { id: 1, code: "N01", name: "Test DUN", state: "Johor", constituency_code: "P140", adun_name: "", adun_party: "" },
        ],
      }),
    });

    const result = await fetchDUNs({ constituency: "P140" });
    expect(result).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("constituency=P140")
    );
  });
});

describe("fetchDUNDetail", () => {
  it("fetches DUN detail by ID", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 1,
        code: "N01",
        name: "Buloh Kasap",
        state: "Johor",
        constituency_code: "P140",
        constituency_name: "Segamat",
        adun_name: "Test ADUN",
        adun_party: "BN",
        adun_coalition: "",
        indian_population: 1000,
        indian_percentage: 8.5,
        schools: [],
      }),
    });

    const result = await fetchDUNDetail(1);
    expect(result.code).toBe("N01");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/duns/1/")
    );
  });
});

describe("fetchDUNGeoJSON", () => {
  it("returns null on error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });

    const result = await fetchDUNGeoJSON(999);
    expect(result).toBeNull();
  });
});
