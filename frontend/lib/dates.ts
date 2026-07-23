/**
 * Shared date formatting.
 *
 * Always pass an explicit `timeZone`. Without one, `toLocaleDateString` uses the
 * runtime's zone — which is UTC on Cloud Run, not Malaysia. Server-rendered
 * timestamps published between 00:00 and 08:00 MYT then displayed the previous
 * day, making the News page read as up to a day staler than it actually was.
 */
export const MALAYSIA_TIME_ZONE = "Asia/Kuala_Lumpur";

/** Format an ISO timestamp or date string as e.g. "21 July 2026", in Malaysia time. */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: MALAYSIA_TIME_ZONE,
  });
}
