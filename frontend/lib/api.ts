import {
  AuthUser,
  Constituency,
  ConstituencyDetail,
  DUN,
  DUNDetail,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
  MagicLinkResponse,
  NationalStats,
  NewsArticle,
  PaginatedResponse,
  PreferenceUpdate,
  School,
  SchoolConfirmResponse,
  SchoolDetail,
  SchoolEditData,
  SchoolMention,
  SearchResults,
  SubscribeRequest,
  SubscriberResponse,
  UnsubscribeResponse,
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
 * Fetch news articles for a school.
 * Returns empty array if endpoint not available yet.
 */
export async function fetchSchoolNews(
  moeCode: string
): Promise<NewsArticle[]> {
  try {
    return await fetchJSON<NewsArticle[]>(
      `${BASE}/schools/${moeCode}/news/`
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

/**
 * Request a magic link for the given MOE email.
 */
export async function requestMagicLink(
  email: string
): Promise<MagicLinkResponse> {
  const res = await fetch(`${BASE}/auth/request-magic-link/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Verify a magic link token.
 */
export async function verifyMagicLink(
  token: string
): Promise<AuthUser> {
  const res = await fetch(`${BASE}/auth/verify/${token}/`, {
    credentials: "include",
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Get current authenticated user.
 */
export async function fetchMe(): Promise<AuthUser | null> {
  try {
    const res = await fetch(`${BASE}/auth/me/`, {
      credentials: "include",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch school edit data (requires Magic Link session).
 */
export async function fetchSchoolEdit(
  moeCode: string
): Promise<SchoolEditData> {
  const res = await fetch(`${BASE}/schools/${moeCode}/edit/`, {
    credentials: "include",
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Update school data (requires Magic Link session).
 */
export async function updateSchool(
  moeCode: string,
  updates: Partial<SchoolEditData>
): Promise<SchoolEditData> {
  const res = await fetch(`${BASE}/schools/${moeCode}/edit/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(updates),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Confirm school data without editing (requires Magic Link session).
 */
export async function confirmSchool(
  moeCode: string
): Promise<SchoolConfirmResponse> {
  const res = await fetch(`${BASE}/schools/${moeCode}/confirm/`, {
    method: "POST",
    credentials: "include",
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Subscribe to SJK(T) Connect communications.
 * Idempotent — duplicate email reactivates existing subscription.
 */
export async function subscribe(
  request: SubscribeRequest
): Promise<SubscriberResponse> {
  const res = await fetch(`${BASE}/subscribers/subscribe/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.email?.[0] || data.detail || `API error: ${res.status}`);
  }
  return data;
}

/**
 * One-click unsubscribe via token.
 */
export async function unsubscribe(
  token: string
): Promise<UnsubscribeResponse> {
  const res = await fetch(`${BASE}/subscribers/unsubscribe/${token}/`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Fetch subscription preferences by token.
 */
export async function fetchPreferences(
  token: string
): Promise<SubscriberResponse> {
  const res = await fetch(`${BASE}/subscribers/preferences/${token}/`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Update subscription preferences by token.
 */
export async function updatePreferences(
  token: string,
  preferences: PreferenceUpdate
): Promise<SubscriberResponse> {
  const res = await fetch(`${BASE}/subscribers/preferences/${token}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return data;
}

/**
 * Fetch national aggregate statistics for all active Tamil schools.
 */
export async function fetchNationalStats(): Promise<NationalStats> {
  return fetchJSON<NationalStats>(`${BASE}/stats/national/`);
}
