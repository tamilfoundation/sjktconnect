import {
  subscribe,
  unsubscribe,
  fetchPreferences,
  updatePreferences,
} from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

describe("subscribe", () => {
  it("sends POST with email, name, and organisation", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: "user@example.com",
        name: "Test",
        organisation: "PIBG",
        is_active: true,
        subscribed_at: "2026-03-01T00:00:00Z",
        preferences: { PARLIAMENT_WATCH: true, NEWS_WATCH: true, MONTHLY_BLAST: true },
      }),
    });

    const result = await subscribe({
      email: "user@example.com",
      name: "Test",
      organisation: "PIBG",
    });
    expect(result.email).toBe("user@example.com");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/subscribers/subscribe/"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "user@example.com",
          name: "Test",
          organisation: "PIBG",
        }),
      })
    );
  });

  it("throws on invalid email", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        email: ["Enter a valid email address."],
      }),
    });

    await expect(
      subscribe({ email: "not-an-email" })
    ).rejects.toThrow(/Enter a valid email address/);
  });

  it("handles duplicate email (returns 200)", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: "user@example.com",
        name: "",
        organisation: "",
        is_active: true,
        subscribed_at: "2026-03-01T00:00:00Z",
        preferences: {},
      }),
    });

    const result = await subscribe({ email: "user@example.com" });
    expect(result.is_active).toBe(true);
  });
});

describe("unsubscribe", () => {
  it("sends GET with token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        detail: "You have been unsubscribed.",
        email: "user@example.com",
      }),
    });

    const result = await unsubscribe("abc-123");
    expect(result.email).toBe("user@example.com");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/subscribers/unsubscribe/abc-123/")
    );
  });

  it("throws on invalid token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Invalid unsubscribe link." }),
    });

    await expect(unsubscribe("bad-token")).rejects.toThrow(
      /Invalid unsubscribe link/
    );
  });
});

describe("fetchPreferences", () => {
  it("sends GET with token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: "user@example.com",
        name: "",
        organisation: "",
        is_active: true,
        subscribed_at: "2026-03-01T00:00:00Z",
        preferences: {
          PARLIAMENT_WATCH: true,
          NEWS_WATCH: false,
          MONTHLY_BLAST: true,
        },
      }),
    });

    const result = await fetchPreferences("pref-token");
    expect(result.preferences.NEWS_WATCH).toBe(false);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/subscribers/preferences/pref-token/")
    );
  });

  it("throws on invalid token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Invalid preferences link." }),
    });

    await expect(fetchPreferences("bad-token")).rejects.toThrow(
      /Invalid preferences link/
    );
  });
});

describe("updatePreferences", () => {
  it("sends PUT with preferences", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: "user@example.com",
        name: "",
        organisation: "",
        is_active: true,
        subscribed_at: "2026-03-01T00:00:00Z",
        preferences: {
          PARLIAMENT_WATCH: false,
          NEWS_WATCH: true,
          MONTHLY_BLAST: true,
        },
      }),
    });

    const result = await updatePreferences("pref-token", {
      PARLIAMENT_WATCH: false,
    });
    expect(result.preferences.PARLIAMENT_WATCH).toBe(false);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/subscribers/preferences/pref-token/"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ PARLIAMENT_WATCH: false }),
      })
    );
  });

  it("throws on invalid token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Invalid preferences link." }),
    });

    await expect(
      updatePreferences("bad-token", { NEWS_WATCH: false })
    ).rejects.toThrow(/Invalid preferences link/);
  });
});
