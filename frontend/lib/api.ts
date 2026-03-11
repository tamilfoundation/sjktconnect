import {
  AuthUser,
  Constituency,
  ConstituencyDetail,
  ConstituencyMention,
  DUN,
  DUNDetail,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
  HansardMention,
  MagicLinkResponse,
  MeetingReport,
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
  SittingBrief,
  SubscribeRequest,
  SubscriberResponse,
  Suggestion,
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
 * Fetch paginated news articles with optional filters.
 */
export async function fetchNews(options?: {
  category?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<PaginatedResponse<NewsArticle>> {
  let url = `${BASE}/news/?page_size=${options?.pageSize ?? 20}`;
  if (options?.category && options.category !== "all") {
    url += `&category=${encodeURIComponent(options.category)}`;
  }
  if (options?.search) {
    url += `&search=${encodeURIComponent(options.search)}`;
  }
  if (options?.page && options.page > 1) {
    url += `&page=${options.page}`;
  }
  return fetchJSON<PaginatedResponse<NewsArticle>>(url);
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
): Promise<SubscriberResponse & { is_new: boolean }> {
  const res = await fetch(`${BASE}/subscribers/subscribe/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const data = await res.json();
  if (!res.ok) {
    const fieldError = Object.values(data).flat().find((v) => typeof v === "string");
    throw new Error(data.email?.[0] || data.detail || (typeof fieldError === "string" ? fieldError : null) || `API error: ${res.status}`);
  }
  return { ...data, is_new: res.status === 201 };
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

/**
 * Fetch Hansard mentions for a constituency's MP.
 */
export async function fetchConstituencyMentions(
  code: string
): Promise<ConstituencyMention[]> {
  try {
    return await fetchJSON<ConstituencyMention[]>(
      `${BASE}/constituencies/${code}/mentions/`
    );
  } catch {
    return [];
  }
}

/**
 * Fetch sitting briefs (parliament watch summaries).
 */
export async function fetchBriefs(): Promise<SittingBrief[]> {
  try {
    const page = await fetchJSON<PaginatedResponse<SittingBrief>>(
      `${BASE}/briefs/`
    );
    return page.results;
  } catch {
    return [];
  }
}

/**
 * Fetch a single sitting brief by ID.
 */
export async function fetchBrief(id: number): Promise<SittingBrief | null> {
  try {
    return await fetchJSON<SittingBrief>(`${BASE}/briefs/${id}/`);
  } catch {
    return null;
  }
}

export async function fetchAllMentions(): Promise<HansardMention[]> {
  try {
    const results: HansardMention[] = [];
    let url: string | null = `${BASE}/mentions/`;
    while (url) {
      const page = await fetchJSON<PaginatedResponse<HansardMention>>(url);
      results.push(...page.results);
      url = page.next;
    }
    return results;
  } catch {
    return [];
  }
}

/**
 * Fetch parliamentary meeting reports.
 */
export async function fetchMeetingReports(): Promise<MeetingReport[]> {
  try {
    return await fetchJSON<MeetingReport[]>(`${BASE}/meetings/`);
  } catch {
    return [];
  }
}

/**
 * Fetch a single parliamentary meeting report by ID.
 */
/**
 * Create a suggestion for a school (requires session).
 */
export async function createSuggestion(
  moeCode: string,
  data: {
    type: string;
    field_name?: string;
    suggested_value?: string;
    note?: string;
    image?: string;
  }
): Promise<Suggestion> {
  const res = await fetch(`${BASE}/schools/${moeCode}/suggestions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Fetch suggestions for a school.
 */
export async function fetchSuggestions(
  moeCode: string
): Promise<Suggestion[]> {
  const res = await fetch(`${BASE}/schools/${moeCode}/suggestions/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch suggestions");
  return res.json();
}

/**
 * Fetch all suggestions by the current user.
 */
export async function fetchMySuggestions(): Promise<Suggestion[]> {
  const res = await fetch(`${BASE}/suggestions/mine/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch suggestions");
  return res.json();
}

/**
 * Fetch pending suggestions for moderation.
 */
export async function fetchPendingSuggestions(): Promise<Suggestion[]> {
  const res = await fetch(`${BASE}/suggestions/pending/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch pending suggestions");
  return res.json();
}

/**
 * Approve a suggestion.
 */
export async function approveSuggestion(id: number): Promise<Suggestion> {
  const res = await fetch(`${BASE}/suggestions/${id}/approve/`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to approve suggestion");
  return res.json();
}

/**
 * Reject a suggestion with a reason.
 */
export async function rejectSuggestion(id: number, reason: string): Promise<Suggestion> {
  const res = await fetch(`${BASE}/suggestions/${id}/reject/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to reject suggestion");
  return res.json();
}

export async function fetchMeetingReport(id: number): Promise<MeetingReport | null> {
  try {
    return await fetchJSON<MeetingReport>(`${BASE}/meetings/${id}/`);
  } catch {
    return null;
  }
}
