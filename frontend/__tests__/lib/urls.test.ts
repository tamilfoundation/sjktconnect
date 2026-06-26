import {
  schoolPath,
  parseSchoolSlug,
  isCanonicalSchoolSlug,
} from "@/lib/urls";

describe("schoolPath", () => {
  it("builds slug with name + city + moe_code", () => {
    expect(
      schoolPath({
        moe_code: "PBD1088",
        short_name: "SJK(T) Subramaniya Barathee",
        city: "Gelugor",
      }),
    ).toBe("/school/subramaniya-barathee-gelugor-pbd1088");
  });

  it("strips the SJK(T) prefix from the name", () => {
    expect(
      schoolPath({
        moe_code: "JBD0050",
        short_name: "SJK(T) Ladang Bikam",
        city: "Segamat",
      }),
    ).toBe("/school/ladang-bikam-segamat-jbd0050");
  });

  it("handles SJKT (no brackets) prefix", () => {
    expect(
      schoolPath({
        moe_code: "JBD0050",
        short_name: "SJKT Test School",
        city: "Town",
      }),
    ).toBe("/school/test-school-town-jbd0050");
  });

  it("collapses non-alphanumeric chars to hyphens", () => {
    expect(
      schoolPath({
        moe_code: "MBD0067",
        short_name: "SJK(T) Ldg West Country 'Timur'",
        city: "Klang",
      }),
    ).toBe("/school/ldg-west-country-timur-klang-mbd0067");
  });

  it("falls back to just moe_code when no name + no city", () => {
    expect(schoolPath({ moe_code: "PBD1088" })).toBe("/school/pbd1088");
  });

  it("works when only short_name present", () => {
    expect(
      schoolPath({ moe_code: "PBD1088", short_name: "SJK(T) Foo" }),
    ).toBe("/school/foo-pbd1088");
  });
});

describe("parseSchoolSlug", () => {
  it("extracts moe_code from full slug", () => {
    expect(parseSchoolSlug("subramaniya-barathee-gelugor-pbd1088")).toBe("PBD1088");
    expect(parseSchoolSlug("ladang-bikam-segamat-jbd0050")).toBe("JBD0050");
  });

  it("accepts bare moe_code (legacy URLs)", () => {
    expect(parseSchoolSlug("PBD1088")).toBe("PBD1088");
    expect(parseSchoolSlug("pbd1088")).toBe("PBD1088");
    expect(parseSchoolSlug("ABDB006")).toBe("ABDB006");
  });

  it("handles 4-letter + 3-digit moe_code shape", () => {
    expect(parseSchoolSlug("jendarata-bahagian-alpha-bernam-abdb006")).toBe("ABDB006");
  });

  it("returns null for invalid slugs", () => {
    expect(parseSchoolSlug("")).toBeNull();
    expect(parseSchoolSlug("just-a-name-no-code")).toBeNull();
    expect(parseSchoolSlug("foo-bar-baz")).toBeNull();
    expect(parseSchoolSlug("notavalidcode")).toBeNull();
  });
});

describe("isCanonicalSchoolSlug", () => {
  const school = {
    moe_code: "PBD1088",
    short_name: "SJK(T) Subramaniya Barathee",
    city: "Gelugor",
  };

  it("recognises the canonical slug", () => {
    expect(
      isCanonicalSchoolSlug("subramaniya-barathee-gelugor-pbd1088", school),
    ).toBe(true);
  });

  it("flags the bare-code form as non-canonical", () => {
    expect(isCanonicalSchoolSlug("PBD1088", school)).toBe(false);
    expect(isCanonicalSchoolSlug("pbd1088", school)).toBe(false);
  });

  it("flags a stale slug (after a name change) as non-canonical", () => {
    expect(
      isCanonicalSchoolSlug("old-name-gelugor-pbd1088", school),
    ).toBe(false);
  });
});
