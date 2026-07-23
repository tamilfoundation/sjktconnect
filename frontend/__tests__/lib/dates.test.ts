import { formatDate } from "@/lib/dates";

describe("formatDate", () => {
  it("returns empty string for null", () => {
    expect(formatDate(null)).toBe("");
  });

  it("formats a date as en-GB long form", () => {
    expect(formatDate("2026-03-01T10:00:00Z")).toBe("1 March 2026");
  });

  // Regression: the news date bug found 2026-07-23. This article was published
  // 21 July 07:59 MYT (23:59 UTC on the 20th). Formatting without an explicit
  // timeZone used the Cloud Run runtime zone (UTC) and rendered "20 July 2026",
  // making the News page look a day staler than it was.
  it("renders early-morning MYT timestamps on the correct Malaysian day", () => {
    expect(formatDate("2026-07-21T07:59:28+08:00")).toBe("21 July 2026");
  });

  it("does not shift dates for timestamps later in the Malaysian day", () => {
    expect(formatDate("2026-07-21T23:30:00+08:00")).toBe("21 July 2026");
  });

  it("keeps date-only strings on the same day", () => {
    expect(formatDate("2026-07-21")).toBe("21 July 2026");
  });
});
