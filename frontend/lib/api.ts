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
  MeetingReport,
  NationalStats,
  NewsArticle,
  PaginatedResponse,
  PreferenceUpdate,
  School,
  SchoolDetail,
  SchoolEditData,
  SchoolImageData,
  SchoolLeaderAdminData,
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

// Sprint 21: Next 15+ defaults fetch() to uncached, which marks every
// server-rendered page as dynamic and breaks the page-level
// `revalidate = 86400` contract. Opt back into ISR caching so the
// pages set up in Sprint 17 actually get cached at the data layer.
// All authenticated endpoints below use direct fetch() with
// credentials:"include" and bypass this helper, so they're unaffected.
async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { next: { revalidate: 86400 } });
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
 * Fetch all schools with minimal fields for map display.
 * Single request (~50 KB vs ~550 KB from fetchAllSchools).
 */
export async function fetchMapSchools(): Promise<School[]> {
  return fetchJSON<School[]>(`${BASE}/schools/map/`);
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
 * Update the current user's own display_name.
 */
export async function updateMyProfile(
  displayName: string,
): Promise<AuthUser> {
  const res = await fetch(`${BASE}/auth/me/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.display_name?.[0] || err.detail || "Update failed");
  }
  return res.json();
}

// --- SUPERADMIN user management ---

export interface AdminUserRow {
  id: number;
  display_name: string;
  avatar_url: string;
  email: string;
  role: "SUPERADMIN" | "MODERATOR" | "USER";
  admin_school: { moe_code: string; name: string } | null;
  points: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListFilters {
  role?: string;
  has_admin_school?: "true" | "false";
  is_active?: "true" | "false";
  search?: string;
  page?: number;
}

export async function fetchAdminUsers(
  filters: AdminUserListFilters = {},
): Promise<{ count: number; next: string | null; previous: string | null; results: AdminUserRow[] }> {
  const qs = new URLSearchParams();
  if (filters.role) qs.set("role", filters.role);
  if (filters.has_admin_school) qs.set("has_admin_school", filters.has_admin_school);
  if (filters.is_active) qs.set("is_active", filters.is_active);
  if (filters.search) qs.set("search", filters.search);
  if (filters.page) qs.set("page", String(filters.page));
  const res = await fetch(`${BASE}/auth/admin/users/?${qs.toString()}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to load users");
  return res.json();
}

export async function updateAdminUser(
  id: number,
  patch: { role?: string; admin_school?: string | null; is_active?: boolean },
): Promise<AdminUserRow> {
  const res = await fetch(`${BASE}/auth/admin/users/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.admin_school?.[0] || err.role?.[0] || "Update failed");
  }
  return res.json();
}

export async function deactivateAdminUser(id: number): Promise<void> {
  const res = await fetch(`${BASE}/auth/admin/users/${id}/`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Deactivate failed");
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

// Sprint 19 (2026-04-28): confirmSchool() removed. The /schools/<moe>/confirm/
// endpoint and its UI have been retired — MOE data is the source of truth,
// nothing for school admins to confirm. See decisions.md Sprint 19 entry.

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
 * Create a non-photo suggestion (DATA_CORRECTION, NOTE).
 *
 * Photo uploads use uploadSchoolPhoto() — different endpoint, multipart form.
 */
export async function createSuggestion(
  moeCode: string,
  data: {
    type: "DATA_CORRECTION" | "NOTE";
    field_name?: string;
    suggested_value?: string;
    note?: string;
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

/** Stable error codes the photo-upload backend returns. */
export type PhotoUploadErrorCode =
  | "missing_image"
  | "too_large"
  | "too_small"
  | "unsupported_format"
  | "invalid_image"
  | "duplicate"
  | "throttled"
  | "unknown";

export class PhotoUploadError extends Error {
  code: PhotoUploadErrorCode;
  status: number;
  constructor(code: PhotoUploadErrorCode, status: number, message: string) {
    super(message);
    // tsconfig target is es5; `extends Error` loses the prototype chain
    // without this fix-up, breaking `instanceof PhotoUploadError`.
    Object.setPrototypeOf(this, PhotoUploadError.prototype);
    this.name = "PhotoUploadError";
    this.code = code;
    this.status = status;
  }
}

/**
 * Upload a photo to a school as a PENDING suggestion (Sprint 14).
 * Multipart endpoint with server-side Pillow validation. Throws
 * PhotoUploadError with a stable code on validation/throttle failures.
 */
export async function uploadSchoolPhoto(
  moeCode: string,
  file: File,
  note: string = "",
): Promise<Suggestion> {
  const form = new FormData();
  form.append("image", file);
  if (note) form.append("note", note);
  const res = await fetch(
    `${BASE}/schools/${moeCode}/suggestions/photo/`,
    { method: "POST", credentials: "include", body: form },
  );
  if (res.ok) return res.json();
  let payload: { code?: string; detail?: string } = {};
  try {
    payload = await res.json();
  } catch {
    // ignore — body may be HTML or empty
  }
  const code = (payload.code as PhotoUploadErrorCode) ||
    (res.status === 429 ? "throttled" : "unknown");
  const detail = payload.detail || `HTTP ${res.status}`;
  throw new PhotoUploadError(code, res.status, detail);
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

/**
 * Fetch images for a school (public).
 */
export async function fetchSchoolImages(moeCode: string): Promise<SchoolImageData[]> {
  const res = await fetch(`${API_URL}/api/v1/schools/${moeCode}/images/`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch images");
  return res.json();
}

/**
 * Reorder images for a school (admin/superadmin).
 */
export async function reorderSchoolImages(moeCode: string, order: number[]): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/schools/${moeCode}/images/reorder/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ order }),
  });
  if (!res.ok) throw new Error("Failed to reorder images");
}

/**
 * Delete an image from a school (admin/superadmin).
 */
export async function deleteSchoolImage(moeCode: string, imageId: number): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/schools/${moeCode}/images/${imageId}/`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to delete image");
}

/**
 * Update an image's caption (Sprint 15).
 * Permission: SUPERADMIN or this school's admin. Server caps at 200 chars.
 */
export async function updateImageCaption(
  moeCode: string,
  imageId: number,
  caption: string,
): Promise<{ id: number; caption: string }> {
  const res = await fetch(
    `${API_URL}/api/v1/schools/${moeCode}/images/${imageId}/caption/`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ caption }),
    },
  );
  if (!res.ok) {
    let detail = "Failed to save caption";
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

/**
 * Make this image the school's hero (is_primary=true).
 * Permission: SUPERADMIN or this school's admin (Sprint 14).
 */
export async function pinSchoolImage(moeCode: string, imageId: number): Promise<void> {
  const res = await fetch(
    `${API_URL}/api/v1/schools/${moeCode}/images/${imageId}/pin/`,
    { method: "POST", credentials: "include" },
  );
  if (!res.ok) throw new Error("Failed to set hero photo");
}

/**
 * Approve a photo suggestion. Surfaces 409 (slot_full) as a typed error so
 * the UI can show "Delete an existing photo first" instead of a generic
 * failure message.
 */
export async function approvePhotoSuggestion(id: number): Promise<{
  ok: boolean;
  slot_full?: boolean;
  detail?: string;
  suggestion?: Suggestion;
}> {
  const res = await fetch(`${BASE}/suggestions/${id}/approve/`, {
    method: "POST",
    credentials: "include",
  });
  if (res.ok) {
    return { ok: true, suggestion: await res.json() };
  }
  if (res.status === 409) {
    let payload: { code?: string; detail?: string } = {};
    try {
      payload = await res.json();
    } catch { /* empty */ }
    if (payload.code === "slot_full") {
      return { ok: false, slot_full: true, detail: payload.detail };
    }
  }
  return { ok: false, detail: await res.text() };
}

// ----- School leader CRUD (Sprint 20) -----

export type LeaderRole =
  | "board_chair"
  | "headmaster"
  | "pta_chair"
  | "alumni_chair";

export interface LeaderUpsertPayload {
  name: string;
  phone?: string;
  email?: string;
}

export async function createSchoolLeader(
  moeCode: string,
  role: LeaderRole,
  payload: LeaderUpsertPayload,
): Promise<SchoolLeaderAdminData> {
  const res = await fetch(`${BASE}/schools/${moeCode}/leaders/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, ...payload }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return data;
}

export async function updateSchoolLeader(
  moeCode: string,
  leaderId: number,
  payload: LeaderUpsertPayload,
): Promise<SchoolLeaderAdminData> {
  const res = await fetch(`${BASE}/schools/${moeCode}/leaders/${leaderId}/`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `API error: ${res.status}`);
  }
  return data;
}

export async function deleteSchoolLeader(
  moeCode: string,
  leaderId: number,
): Promise<void> {
  const res = await fetch(`${BASE}/schools/${moeCode}/leaders/${leaderId}/`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error: ${res.status}`);
  }
}

// ----- Sprint 27 #1+#4 — explicit ISR cache invalidation after admin edits -----

/**
 * Tell the Next.js server to re-render the public school detail page
 * for `/{locale}/school/{moeCode}` across all 3 locales. Without this,
 * the page's `revalidate=86400` cache holds stale data for up to 24h
 * after a school admin saves their edit.
 *
 * Hits the Next route handler at `/api/revalidate` (same-origin), NOT
 * the Django API. Fire-and-forget semantics — callers should swallow
 * exceptions so a network blip here doesn't block the post-save flow.
 */
export async function revalidateSchoolPage(moeCode: string): Promise<void> {
  const res = await fetch("/api/revalidate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "school", key: moeCode }),
  });
  if (!res.ok) {
    throw new Error(`revalidate failed: ${res.status}`);
  }
}
