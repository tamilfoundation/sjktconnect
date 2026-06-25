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
