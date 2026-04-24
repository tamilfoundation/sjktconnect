import { fetchMe } from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

describe("fetchMe", () => {
  it("returns user when authenticated", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 1,
        google_id: "g-1",
        display_name: "Test User",
        avatar_url: "",
        role: "USER",
        admin_school: { moe_code: "JBD0050", name: "SJK(T) Ladang Bikam" },
        points: 0,
        is_active: true,
        email: "jbd0050@moe.edu.my",
      }),
    });

    const result = await fetchMe();
    expect(result).not.toBeNull();
    expect(result?.email).toBe("jbd0050@moe.edu.my");
    expect(result?.admin_school?.moe_code).toBe("JBD0050");
  });

  it("returns null when not authenticated", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Not authenticated" }),
    });

    const result = await fetchMe();
    expect(result).toBeNull();
  });

  it("returns null on network error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const result = await fetchMe();
    expect(result).toBeNull();
  });

  it("returns user with no admin_school for community-only profile", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 2,
        google_id: "g-2",
        display_name: "Community User",
        avatar_url: "",
        role: "USER",
        admin_school: null,
        points: 5,
        is_active: true,
        email: "user@gmail.com",
      }),
    });

    const result = await fetchMe();
    expect(result).not.toBeNull();
    expect(result?.admin_school).toBeNull();
  });
});
