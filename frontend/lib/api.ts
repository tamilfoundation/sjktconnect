import {
  Constituency,
  ConstituencyDetail,
  DUN,
  DUNDetail,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
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
 * Fetch all constituencies with optional state filter.
 */
export async function fetchConstituencies(
  state?: string
): Promise<Constituency[]> {
  let url = `${BASE}/constituencies/?page_size=50`;
  if (state) {
    url += `&state=${encodeURIComponent(state)}`;
  }
  const items: Constituency[] = [];
  let page = await fetchJSON<PaginatedResponse<Constituency>>(url);
  items.push(...page.results);
  while (page.next) {
    page = await fetchJSON<PaginatedResponse<Constituency>>(page.next);
    items.push(...page.results);
  }
  return items;
}

/**
 * Fetch a single constituency detail by code.
 */
export async function fetchConstituencyDetail(
  code: string
): Promise<ConstituencyDetail> {
  return fetchJSON<ConstituencyDetail>(`${BASE}/constituencies/${code}/`);
}

/**
 * Fetch constituency boundary GeoJSON.
 */
export async function fetchConstituencyGeoJSON(
  code: string
): Promise<GeoJSONFeature | null> {
  try {
    return await fetchJSON<GeoJSONFeature>(
      `${BASE}/constituencies/${code}/geojson/`
    );
  } catch {
    return null;
  }
}

/**
 * Fetch all DUNs with optional filters.
 */
export async function fetchDUNs(
  options?: { state?: string; constituency?: string }
): Promise<DUN[]> {
  let url = `${BASE}/duns/?page_size=50`;
  if (options?.state) {
    url += `&state=${encodeURIComponent(options.state)}`;
  }
  if (options?.constituency) {
    url += `&constituency=${encodeURIComponent(options.constituency)}`;
  }
  const items: DUN[] = [];
  let page = await fetchJSON<PaginatedResponse<DUN>>(url);
  items.push(...page.results);
  while (page.next) {
    page = await fetchJSON<PaginatedResponse<DUN>>(page.next);
    items.push(...page.results);
  }
  return items;
}

/**
 * Fetch a single DUN detail by ID.
 */
export async function fetchDUNDetail(id: number): Promise<DUNDetail> {
  return fetchJSON<DUNDetail>(`${BASE}/duns/${id}/`);
}

/**
 * Fetch DUN boundary GeoJSON.
 */
export async function fetchDUNGeoJSON(
  id: number
): Promise<GeoJSONFeature | null> {
  try {
    return await fetchJSON<GeoJSONFeature>(`${BASE}/duns/${id}/geojson/`);
  } catch {
    return null;
  }
}

/**
 * Get unique states from a list of schools.
 */
export function getUniqueStates(schools: School[]): string[] {
  const states = new Set(schools.map((s) => s.state));
  return Array.from(states).sort();
}
