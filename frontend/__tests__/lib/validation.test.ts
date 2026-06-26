import {
  PHONE_PATTERN_RE,
  EMAIL_PATTERN_RE,
  isValidPhone,
  isValidEmail,
} from "@/lib/validation";

describe("validation helpers", () => {
  describe("isValidPhone", () => {
    it("accepts empty (treated as 'no value')", () => {
      expect(isValidPhone("")).toBe(true);
    });
    it("accepts common Malaysian shapes", () => {
      expect(isValidPhone("+60 4 966 3429")).toBe(true);
      expect(isValidPhone("04-966 3429")).toBe(true);
      expect(isValidPhone("03-2601 7222")).toBe(true);
      expect(isValidPhone("(03) 2601 7222")).toBe(true);
      expect(isValidPhone("+60123456789")).toBe(true);
    });
    it("rejects multi-number values with /", () => {
      expect(isValidPhone("05-2421470/011-2379104")).toBe(false);
    });
    it("rejects letters", () => {
      expect(isValidPhone("call 03-1234")).toBe(false);
      expect(isValidPhone("EXT 123")).toBe(false);
    });
    it("rejects too-short / too-long", () => {
      expect(isValidPhone("123")).toBe(false);
      expect(isValidPhone("1".repeat(25))).toBe(false);
    });
    // Sprint 28: tightened to MY-specific digit-count rule.
    it("rejects truncated mobile (Sprint 28 owner-reported case)", () => {
      // 012-2090008 is 10 digits but that's only valid for landline.
      // Mobile starting 01 needs 10-11 digits with 01X prefix; this is
      // exactly the case where the user truncated and Sprint 27 let it
      // through. Owner said "0122090008" — 10 digits — that one
      // actually IS valid (012 + 7 digits = 10 total). Test the truly-
      // truncated case below:
      expect(isValidPhone("012209000")).toBe(false); // 9 digits, short
      expect(isValidPhone("012209")).toBe(false);     // way short
    });
    it("rejects truncated landline", () => {
      expect(isValidPhone("06791")).toBe(false);      // 5 digits
      expect(isValidPhone("06-79125")).toBe(false);    // 7 digits
    });
    it("accepts canonical Malaysian shapes (digit-count check)", () => {
      // Mobile 10 digits: 012 + 7
      expect(isValidPhone("0122090008")).toBe(true);
      // Mobile 11 digits: 011 + 8
      expect(isValidPhone("01123456789")).toBe(true);
      // Landline 10 digits: 03 + 8
      expect(isValidPhone("0326017222")).toBe(true);
      // Landline 9 digits: 04 + 7
      expect(isValidPhone("049663429")).toBe(true);
      // With +60 prefix
      expect(isValidPhone("+60 12 209 0008")).toBe(true);
      expect(isValidPhone("+60-6 791 2521")).toBe(true);
    });
    it("rejects numbers not starting with 0", () => {
      expect(isValidPhone("9876543210")).toBe(false);
      expect(isValidPhone("1234567890")).toBe(false);
    });
  });

  describe("isValidEmail", () => {
    it("accepts empty", () => {
      expect(isValidEmail("")).toBe(true);
    });
    it("accepts realistic addresses", () => {
      expect(isValidEmail("a@b.co")).toBe(true);
      expect(isValidEmail("kbd6019@moe.edu.my")).toBe(true);
      expect(isValidEmail("name+tag@example.com")).toBe(true);
    });
    it("rejects malformed", () => {
      expect(isValidEmail("plainstring")).toBe(false);
      expect(isValidEmail("@noatstart.com")).toBe(false);
      expect(isValidEmail("missing-domain@")).toBe(false);
      expect(isValidEmail("two spaces in @example.com")).toBe(false);
    });
  });

  it("regex constants are exported and match helpers", () => {
    expect(PHONE_PATTERN_RE.test("03-1234567")).toBe(true);
    expect(EMAIL_PATTERN_RE.test("a@b.co")).toBe(true);
  });
});
