import { fetchSchoolEdit, updateSchool, confirmSchool } from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockClear();
});

describe("fetchSchoolEdit", () => {
  it("sends GET with credentials", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        moe_code: "JBD0050",
        name: "SJK(T) Ladang Bikam",
        phone: "07-1234567",
      }),
    });

    const result = await fetchSchoolEdit("JBD0050");
    expect(result.moe_code).toBe("JBD0050");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/schools/JBD0050/edit/"),
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("throws on 403 (not authenticated)", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: "You must be logged in via a magic link to perform this action.",
      }),
    });

    await expect(fetchSchoolEdit("JBD0050")).rejects.toThrow(/magic link/);
  });
});

describe("updateSchool", () => {
  it("sends PUT with credentials and JSON body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        moe_code: "JBD0050",
        phone: "07-9999999",
      }),
    });

    const result = await updateSchool("JBD0050", { phone: "07-9999999" });
    expect(result.phone).toBe("07-9999999");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/schools/JBD0050/edit/"),
      expect.objectContaining({
        method: "PUT",
        credentials: "include",
        body: JSON.stringify({ phone: "07-9999999" }),
      })
    );
  });

  it("throws on wrong school", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: "You can only edit your own school." }),
    });

    await expect(
      updateSchool("JBD0099", { phone: "07-9999999" })
    ).rejects.toThrow(/own school/);
  });
});

describe("confirmSchool", () => {
  it("sends POST with credentials", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        message: "School data confirmed.",
        last_verified: "2026-02-27T12:00:00Z",
        verified_by: "jbd0050@moe.edu.my",
      }),
    });

    const result = await confirmSchool("JBD0050");
    expect(result.message).toBe("School data confirmed.");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/schools/JBD0050/confirm/"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });

  it("throws on not authenticated", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: "You must be logged in via a magic link to perform this action.",
      }),
    });

    await expect(confirmSchool("JBD0050")).rejects.toThrow(/magic link/);
  });
});
