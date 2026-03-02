import en from "../../messages/en.json";
import ta from "../../messages/ta.json";
import ms from "../../messages/ms.json";

function getKeys(obj: any, prefix = ""): string[] {
  const keys: string[] = [];
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === "object" && obj[key] !== null) {
      keys.push(...getKeys(obj[key], fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

describe("Translation completeness", () => {
  const enKeys = getKeys(en);

  it("Tamil translations have all English keys", () => {
    const taKeys = getKeys(ta);
    const missing = enKeys.filter((k) => !taKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("Malay translations have all English keys", () => {
    const msKeys = getKeys(ms);
    const missing = enKeys.filter((k) => !msKeys.includes(k));
    expect(missing).toEqual([]);
  });

  it("no extra keys in Tamil that are not in English", () => {
    const taKeys = getKeys(ta);
    const extra = taKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });

  it("no extra keys in Malay that are not in English", () => {
    const msKeys = getKeys(ms);
    const extra = msKeys.filter((k) => !enKeys.includes(k));
    expect(extra).toEqual([]);
  });
});
