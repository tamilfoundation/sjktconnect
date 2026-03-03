/**
 * Display mappings for MOE database values.
 * Translates raw MOE codes/abbreviations into human-readable English.
 */

export const ASSISTANCE_TYPE: Record<string, string> = {
  SBK: "Fully Government-Aided",
  SK: "Government School",
  SABK: "Government-Aided Religious",
};

export const LOCATION_TYPE: Record<string, string> = {
  Bandar: "Urban",
  "Luar Bandar": "Rural",
};

export const SESSION_TYPE: Record<string, string> = {
  "Pagi Sahaja": "Morning only",
  "Pagi dan Petang": "Morning and afternoon",
};

/**
 * Check if a value is empty or a placeholder like "TIADA" (Malay for "none").
 */
export function isEmpty(value: string | null | undefined): boolean {
  if (!value) return true;
  const trimmed = value.trim();
  return trimmed === "" || trimmed === "TIADA" || trimmed === "-" || trimmed === "0";
}

/**
 * Translate a raw MOE value using a lookup table, falling back to the original.
 */
export function translate(
  value: string,
  table: Record<string, string>
): string {
  return table[value] || value;
}
