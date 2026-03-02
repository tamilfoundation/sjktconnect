import { routing } from "@/i18n/routing";

describe("i18n routing config", () => {
  it("defines three locales", () => {
    expect(routing.locales).toEqual(["en", "ta", "ms"]);
  });

  it("uses en as default locale", () => {
    expect(routing.defaultLocale).toBe("en");
  });
});
