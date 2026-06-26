import {
  buildAlternates,
  buildSchoolMetadata,
  buildConstituencyMetadata,
  buildDUNMetadata,
  buildSchoolJsonLd,
} from "@/lib/seo";
import type {
  SchoolDetail,
  ConstituencyDetail,
  DUNDetail,
} from "@/lib/types";

const makeSchool = (overrides: Partial<SchoolDetail> = {}): SchoolDetail => ({
  moe_code: "ABDA004",
  name: "SEKOLAH JENIS KEBANGSAAN (TAMIL) TROLAK",
  short_name: "SJK(T) Trolak",
  state: "Perak",
  ppd: "PPD Batang Padang",
  constituency_code: "P074",
  constituency_name: "Tapah",
  enrolment: 17,
  teacher_count: 9,
  gps_lat: 4.0,
  gps_lng: 101.5,
  is_active: true,
  assistance_type: "SK",
  location_type: "Luar Bandar",
  preschool_enrolment: 0,
  special_enrolment: 0,
  dun_id: 100,
  dun_code: "N42",
  dun_name: "Slim",
  image_url: "https://maps.google/streetview?x=1",
  name_tamil: "",
  address: "Pekan Trolak",
  postcode: "35700",
  city: "Trolak",
  email: "abda004@moe.edu.my",
  phone: "05-4561234",
  fax: "",
  gps_verified: true,
  grade: "C",
  session_count: 1,
  session_type: "Pagi Sahaja",
  skm_eligible: false,
  last_verified: null,
  images: [],
  leaders: [],
  bank_name: "",
  bank_account_number: "",
  bank_account_name: "",
  ...overrides,
});

describe("buildAlternates", () => {
  it("builds canonical for the current locale, not always /en/", () => {
    const r = buildAlternates("/school/ABDA004", "ta");
    expect(r.canonical).toBe("https://tamilschool.org/ta/school/ABDA004");
    expect(r.languages.en).toBe("https://tamilschool.org/en/school/ABDA004");
    expect(r.languages.ta).toBe("https://tamilschool.org/ta/school/ABDA004");
    expect(r.languages.ms).toBe("https://tamilschool.org/ms/school/ABDA004");
    expect(r.languages["x-default"]).toBe(
      "https://tamilschool.org/en/school/ABDA004",
    );
  });

  it("handles homepage path '/'", () => {
    const r = buildAlternates("/", "en");
    expect(r.canonical).toBe("https://tamilschool.org/en");
  });
});

describe("buildSchoolMetadata", () => {
  it("includes town in title when town differs from school name", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "en");
    expect(m.title).toContain("SJK(T) Trolak");
    expect(m.title).toContain("17 Students");
    expect(m.title).toContain("Grade C");
    // City "Trolak" overlaps with school name; postcode-town is "Trolak"
    // so location tail collapses to state
    expect(m.title).toContain("Perak");
  });

  it("English description uses Address/Email/Phone labels", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "en");
    expect(m.description).toContain("Address: Pekan Trolak, 35700 Trolak, Perak");
    expect(m.description).toContain("Email: abda004@moe.edu.my");
    expect(m.description).toContain("Phone: 05-4561234");
    expect(m.description).toContain("Location: Rural");
    expect(m.description).toContain("Assistance: Government");
  });

  it("Malay description uses Alamat/E-mel/Telefon labels", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "ms");
    expect(m.description).toContain("Alamat:");
    expect(m.description).toContain("E-mel: abda004@moe.edu.my");
    expect(m.description).toContain("Telefon: 05-4561234");
    expect(m.description).toContain("Jenis Lokasi: Luar Bandar");
    expect(m.description).toContain("Jenis Bantuan: Sekolah Kerajaan");
  });

  it("Tamil description uses Tamil-script labels", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "ta");
    expect(m.description).toContain("முகவரி:");
    expect(m.description).toContain("மின்னஞ்சல்: abda004@moe.edu.my");
    expect(m.description).toContain("தொலைபேசி: 05-4561234");
    expect(m.description).toContain("ஊரகம்"); // location_type Luar Bandar
  });

  it("title uses distinct town when town is not part of the school name", () => {
    const s = makeSchool({
      short_name: "SJK(T) Vallambrosa",
      city: "Sungkai",
    });
    const m = buildSchoolMetadata(s, "en");
    expect(m.title).toContain("Sungkai, Perak");
  });

  it("canonical URL reflects current locale, not /en/ (Sprint 28: now slug)", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "ms");
    expect(m.alternates?.canonical).toBe(
      "https://tamilschool.org/ms/school/trolak-trolak-abda004",
    );
  });

  it("openGraph image is set when school has image_url", () => {
    const s = makeSchool();
    const m = buildSchoolMetadata(s, "en");
    expect(m.openGraph?.images).toBeDefined();
    const imgs = m.openGraph?.images as { url: string }[];
    expect(imgs[0].url).toBe("https://maps.google/streetview?x=1");
  });

  it("openGraph image falls back to /school-placeholder.svg when school has no image", () => {
    const s = makeSchool({ image_url: null });
    const m = buildSchoolMetadata(s, "en");
    const imgs = m.openGraph?.images as { url: string }[];
    expect(imgs[0].url).toBe("https://tamilschool.org/school-placeholder.svg");
  });

  it("falls back to short title when stats are missing", () => {
    const s = makeSchool({ enrolment: 0, grade: "" });
    const m = buildSchoolMetadata(s, "en");
    expect(m.title).toContain("SJK(T) Connect");
  });
});

describe("buildConstituencyMetadata", () => {
  const makeC = (overrides: Partial<ConstituencyDetail> = {}): ConstituencyDetail => ({
    code: "P140",
    name: "Indera Mahkota",
    state: "Pahang",
    mp_name: "Saifuddin Abdullah",
    mp_party: "PH-PKR",
    mp_coalition: "PH",
    indian_population: 12000,
    indian_percentage: 8.0,
    avg_income: null,
    poverty_rate: null,
    gini: null,
    unemployment_rate: null,
    ge15_winning_margin: null,
    ge15_total_voters: null,
    ge15_indian_voter_pct: null,
    electoral_influence: null,
    schools: [],
    scorecard: { total_mentions: 5, substantive_mentions: 3, questions_asked: 2, commitments_made: 1, last_mention_date: "2026-03-01" },
    mp: null,
    ...overrides,
  });

  it("English title leads with name + role + Tamil schools", () => {
    const m = buildConstituencyMetadata(makeC(), "en");
    expect(m.title).toContain("Indera Mahkota");
    expect(m.title).toContain("MP");
    expect(m.title).toContain("Tamil schools");
    expect(m.title).toContain("P140");
    expect(m.title).toContain("Pahang");
  });

  it("description names the MP and counts mentions", () => {
    const m = buildConstituencyMetadata(makeC(), "en");
    expect(m.description).toContain("Saifuddin Abdullah");
    expect(m.description).toContain("PH-PKR");
    expect(m.description).toContain("5 parliamentary mentions");
  });

  it("Malay description uses 'mewakili' verb", () => {
    const m = buildConstituencyMetadata(makeC(), "ms");
    expect(m.description).toContain("mewakili");
    expect(m.description).toContain("sebutan parlimen");
  });

  it("canonical reflects current locale", () => {
    const m = buildConstituencyMetadata(makeC(), "ta");
    expect(m.alternates?.canonical).toBe("https://tamilschool.org/ta/constituency/P140");
  });
});

describe("buildDUNMetadata", () => {
  const makeD = (overrides: Partial<DUNDetail> = {}): DUNDetail => ({
    id: 100,
    code: "N42",
    name: "Slim",
    state: "Perak",
    constituency_code: "P074",
    constituency_name: "Tapah",
    adun_name: "Mohd Khusairi Abdul Talib",
    adun_party: "PN-BERSATU",
    adun_coalition: "PN",
    indian_population: null,
    indian_percentage: null,
    schools: [],
    ...overrides,
  });

  it("English title leads with DUN name + ADUN + Tamil Schools", () => {
    const m = buildDUNMetadata(makeD(), "en");
    expect(m.title).toContain("Slim");
    expect(m.title).toContain("ADUN");
    expect(m.title).toContain("Tamil schools");
    expect(m.title).toContain("N42");
    expect(m.title).toContain("Perak");
  });

  it("description names the ADUN and parent constituency", () => {
    const m = buildDUNMetadata(makeD(), "en");
    expect(m.description).toContain("Slim");
    expect(m.description).toContain("Tapah");
    expect(m.description).toContain("Mohd Khusairi Abdul Talib");
  });

  it("canonical reflects current locale", () => {
    const m = buildDUNMetadata(makeD(), "ms");
    expect(m.alternates?.canonical).toBe("https://tamilschool.org/ms/dun/100");
  });
});

describe("buildSchoolJsonLd", () => {
  it("emits EducationalOrganization with PostalAddress + GeoCoordinates", () => {
    const s = makeSchool();
    const j = buildSchoolJsonLd(s);
    expect(j["@context"]).toBe("https://schema.org");
    expect(j["@type"]).toBe("EducationalOrganization");
    expect(j.name).toBe("SJK(T) Trolak");
    expect(j.email).toBe("abda004@moe.edu.my");
    expect(j.telephone).toBe("05-4561234");
    expect(j.numberOfStudents).toBe(17);
    const addr = j.address as Record<string, string>;
    expect(addr["@type"]).toBe("PostalAddress");
    expect(addr.streetAddress).toBe("Pekan Trolak");
    expect(addr.postalCode).toBe("35700");
    expect(addr.addressRegion).toBe("Perak");
    expect(addr.addressCountry).toBe("MY");
    const geo = j.geo as Record<string, number>;
    expect(geo.latitude).toBe(4.0);
    expect(geo.longitude).toBe(101.5);
  });

  it("strips undefined fields when school has no GPS", () => {
    const s = makeSchool({ gps_lat: null, gps_lng: null });
    const j = buildSchoolJsonLd(s);
    expect(j.geo).toBeUndefined();
  });

  it("falls back to placeholder URL for image when school has no image_url", () => {
    const s = makeSchool({ image_url: null });
    const j = buildSchoolJsonLd(s);
    expect(j.image).toBe("https://tamilschool.org/school-placeholder.svg");
  });

  it("strips undefined fields when school has no email/phone", () => {
    const s = makeSchool({ email: "", phone: "" });
    const j = buildSchoolJsonLd(s);
    expect(j.email).toBeUndefined();
    expect(j.telephone).toBeUndefined();
  });
});
