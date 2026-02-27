import { requestMagicLink, verifyMagicLink, fetchMe } from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

describe("requestMagicLink", () => {
  it("sends POST with email", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        message: "Magic link sent.",
        school_name: "SJK(T) Ladang Bikam",
      }),
    });

    const result = await requestMagicLink("jbd0050@moe.edu.my");
    expect(result.school_name).toBe("SJK(T) Ladang Bikam");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/request-magic-link/"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "jbd0050@moe.edu.my" }),
      })
    );
  });

  it("throws on non-moe email", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: "Only @moe.edu.my email addresses are accepted.",
      }),
    });

    await expect(requestMagicLink("user@gmail.com")).rejects.toThrow(
      /moe.edu.my/
    );
  });

  it("throws on school not found", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: "No school found matching this email address.",
      }),
    });

    await expect(requestMagicLink("unknown@moe.edu.my")).rejects.toThrow(
      /No school found/
    );
  });
});

describe("verifyMagicLink", () => {
  it("sends GET with credentials", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        school_moe_code: "JBD0050",
        school_name: "SJK(T) Ladang Bikam",
        email: "jbd0050@moe.edu.my",
      }),
    });

    const result = await verifyMagicLink("test-token-uuid");
    expect(result.school_moe_code).toBe("JBD0050");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/verify/test-token-uuid/"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("throws on invalid token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: "Invalid or expired token." }),
    });

    await expect(verifyMagicLink("bad-token")).rejects.toThrow(
      /Invalid or expired/
    );
  });
});

describe("fetchMe", () => {
  it("returns user when authenticated", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        school_moe_code: "JBD0050",
        school_name: "SJK(T) Ladang Bikam",
        email: "jbd0050@moe.edu.my",
        name: "",
        role: "",
        verified_at: "2026-02-27T10:00:00Z",
      }),
    });

    const result = await fetchMe();
    expect(result).not.toBeNull();
    expect(result?.school_moe_code).toBe("JBD0050");
  });

  it("returns null when not authenticated", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error: "Not authenticated." }),
    });

    const result = await fetchMe();
    expect(result).toBeNull();
  });

  it("returns null on network error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const result = await fetchMe();
    expect(result).toBeNull();
  });
});
