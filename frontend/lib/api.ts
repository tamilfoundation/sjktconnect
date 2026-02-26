import { PaginatedResponse, School, SearchResults } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BASE = `${API_URL}/api/v1`;

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch all schools across all pages.
 * The API paginates at 50/page, so 528 schools = 11 requests.
 */
export async function fetchAllSchools(
  state?: string
): Promise<School[]> {
  const schools: School[] = [];
  let url = `${BASE}/schools/?page_size=50`;
  if (state) {
    url += `&state=${encodeURIComponent(state)}`;
  }

  // First page
  let page = await fetchJSON<PaginatedResponse<School>>(url);
  schools.push(...page.results);

  // Remaining pages
  while (page.next) {
    page = await fetchJSON<PaginatedResponse<School>>(page.next);
    schools.push(...page.results);
  }

  return schools;
}

/**
 * Search schools and constituencies by query string.
 */
export async function searchEntities(
  query: string
): Promise<SearchResults> {
  if (query.length < 2) {
    return { schools: [], constituencies: [] };
  }
  return fetchJSON<SearchResults>(
    `${BASE}/search/?q=${encodeURIComponent(query)}`
  );
}

/**
 * Get unique states from a list of schools.
 */
export function getUniqueStates(schools: School[]): string[] {
  const states = new Set(schools.map((s) => s.state));
  return Array.from(states).sort();
}
