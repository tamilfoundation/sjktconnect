import {
  PaginatedResponse,
  School,
  SchoolDetail,
  SchoolMention,
  SearchResults,
} from "./types";

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
 * Fetch a single school's full profile by MOE code.
 */
export async function fetchSchoolDetail(
  moeCode: string
): Promise<SchoolDetail> {
  return fetchJSON<SchoolDetail>(`${BASE}/schools/${moeCode}/`);
}

/**
 * Fetch all schools in the same constituency as the given school.
 */
export async function fetchSchoolsByConstituency(
  constituencyCode: string
): Promise<School[]> {
  const page = await fetchJSON<PaginatedResponse<School>>(
    `${BASE}/schools/?constituency=${encodeURIComponent(constituencyCode)}&page_size=50`
  );
  return page.results;
}

/**
 * Fetch parliamentary mentions for a school.
 * Returns empty array if endpoint not available yet.
 */
export async function fetchSchoolMentions(
  moeCode: string
): Promise<SchoolMention[]> {
  try {
    return await fetchJSON<SchoolMention[]>(
      `${BASE}/schools/${moeCode}/mentions/`
    );
  } catch {
    return [];
  }
}

/**
 * Get unique states from a list of schools.
 */
export function getUniqueStates(schools: School[]): string[] {
  const states = new Set(schools.map((s) => s.state));
  return Array.from(states).sort();
}
