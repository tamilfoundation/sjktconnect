import {
  ASSISTANCE_TYPE,
  LOCATION_TYPE,
  SESSION_TYPE,
  isEmpty,
  translate,
} from "@/lib/translations";

describe("translations", () => {
  describe("isEmpty", () => {
    it("returns true for null", () => {
      expect(isEmpty(null)).toBe(true);
    });

    it("returns true for undefined", () => {
      expect(isEmpty(undefined)).toBe(true);
    });

    it("returns true for empty string", () => {
      expect(isEmpty("")).toBe(true);
    });

    it("returns true for whitespace-only string", () => {
      expect(isEmpty("   ")).toBe(true);
    });

    it("returns true for TIADA", () => {
      expect(isEmpty("TIADA")).toBe(true);
    });

    it("returns true for dash", () => {
      expect(isEmpty("-")).toBe(true);
    });

    it("returns true for zero string", () => {
      expect(isEmpty("0")).toBe(true);
    });

    it("returns false for valid value", () => {
      expect(isEmpty("03-12345678")).toBe(false);
    });
  });

  describe("translate", () => {
    it("translates known values", () => {
      expect(translate("SBK", ASSISTANCE_TYPE)).toBe("Fully Government-Aided");
      expect(translate("Bandar", LOCATION_TYPE)).toBe("Urban");
      expect(translate("Luar Bandar", LOCATION_TYPE)).toBe("Rural");
    });

    it("falls back to original for unknown values", () => {
      expect(translate("UNKNOWN", ASSISTANCE_TYPE)).toBe("UNKNOWN");
    });
  });

  describe("lookup tables", () => {
    it("ASSISTANCE_TYPE has expected entries", () => {
      expect(ASSISTANCE_TYPE["SBK"]).toBe("Fully Government-Aided");
      expect(ASSISTANCE_TYPE["SK"]).toBe("Government School");
    });

    it("SESSION_TYPE has expected entries", () => {
      expect(SESSION_TYPE["Pagi Sahaja"]).toBe("Morning only");
      expect(SESSION_TYPE["Pagi dan Petang"]).toBe("Morning and afternoon");
    });
  });
});
