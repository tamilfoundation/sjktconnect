export interface School {
  moe_code: string;
  name: string;
  short_name: string;
  state: string;
  ppd: string;
  constituency_code: string | null;
  constituency_name: string | null;
  enrolment: number;
  teacher_count: number;
  gps_lat: number | null;
  gps_lng: number | null;
  is_active: boolean;
  assistance_type: string;
  location_type: string;
  preschool_enrolment: number;
  special_enrolment: number;
  dun_id: number | null;
  dun_code: string | null;
  dun_name: string | null;
  image_url: string | null;
}

export interface SchoolImageData {
  id: number;
  image_url: string;
  source: "SATELLITE" | "PLACES" | "STREET_VIEW" | "MANUAL" | "COMMUNITY";
  position: number;
  is_primary: boolean;
  attribution: string;
  caption: string;
}

export interface SchoolLeader {
  role: string;
  role_display: string;
  name: string;
}

export interface SchoolDetail extends School {
  name_tamil: string;
  address: string;
  postcode: string;
  city: string;
  email: string;
  phone: string;
  fax: string;
  gps_verified: boolean;
  preschool_enrolment: number;
  special_enrolment: number;
  grade: string;
  assistance_type: string;
  session_count: number;
  session_type: string;
  skm_eligible: boolean;
  location_type: string;
  dun_id: number | null;
  dun_code: string | null;
  dun_name: string | null;
  last_verified: string | null;
  image_url: string | null;
  images: SchoolImageData[];
  leaders: SchoolLeader[];
  bank_name: string;
  bank_account_number: string;
  bank_account_name: string;
  history: { en?: string; ms?: string; ta?: string };
  history_source_urls: string[];
  history_status: "UNVERIFIED" | "SCHOOL_REVIEWED" | "VERIFIED";
  history_updated_at: string | null;
}

export interface SchoolMention {
  sitting_date: string;
  mp_name: string;
  mp_constituency: string;
  mp_party: string;
  mention_type: string;
  significance: number | null;
  sentiment: string;
  ai_summary: string;
  verbatim_quote: string;
}

export interface NewsArticleMention {
  name: string;
  moe_code: string;
}

export interface NewsArticle {
  id: number;
  title: string;
  url: string;
  source_name: string;
  published_date: string | null;
  ai_summary: string;
  sentiment: string;
  is_urgent: boolean;
  urgent_reason: string;
  mentioned_schools: NewsArticleMention[];
  created_at: string;
}

export interface Constituency {
  code: string;
  name: string;
  state: string;
  mp_name: string;
  mp_party: string;
  school_count: number;
}

export interface ConstituencyDetail {
  code: string;
  name: string;
  state: string;
  mp_name: string;
  mp_party: string;
  mp_coalition: string;
  indian_population: number | null;
  indian_percentage: number | null;
  avg_income: number | null;
  poverty_rate: number | null;
  gini: number | null;
  unemployment_rate: number | null;
  ge15_winning_margin: number | null;
  ge15_total_voters: number | null;
  ge15_indian_voter_pct: number | null;
  electoral_influence: ElectoralInfluence | null;
  schools: School[];
  scorecard: Scorecard | null;
  mp: MPProfile | null;
}

export interface ElectoralInfluence {
  indian_voters: number;
  winning_margin: number;
  ratio: number;
  verdict: "kingmaker" | "significant" | "safe_seat";
}

export interface MPProfile {
  name: string;
  photo_url: string;
  party: string;
  email: string | null;
  phone: string | null;
  facebook_url: string | null;
  twitter_url: string | null;
  instagram_url: string | null;
  website_url: string | null;
  service_centre_address: string | null;
  parlimen_profile_url: string | null;
  mymp_profile_url: string | null;
}

export interface Scorecard {
  total_mentions: number;
  substantive_mentions: number;
  questions_asked: number;
  commitments_made: number;
  last_mention_date: string | null;
}

export interface DUN {
  id: number;
  code: string;
  name: string;
  state: string;
  constituency_code: string;
  adun_name: string;
  adun_party: string;
}

export interface DUNDetail {
  id: number;
  code: string;
  name: string;
  state: string;
  constituency_code: string;
  constituency_name: string;
  adun_name: string;
  adun_party: string;
  adun_coalition: string;
  indian_population: number | null;
  indian_percentage: number | null;
  schools: School[];
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: {
    type: string;
    coordinates: number[][][] | number[][][][];
  };
  properties: Record<string, unknown>;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface SearchResults {
  schools: School[];
  constituencies: Constituency[];
}

export interface AuthUser {
  id: number;
  google_id: string;
  display_name: string;
  avatar_url: string;
  role: "SUPERADMIN" | "MODERATOR" | "USER";
  admin_school: { moe_code: string; name: string } | null;
  points: number;
  is_active: boolean;
  email: string;
}

export interface ApiError {
  error: string;
}

export interface SchoolLeaderData {
  role: string;
  role_display: string;
  name: string;
}

// Sprint 20: extended shape returned by the admin CRUD endpoints —
// includes id + private fields (phone, email). Backwards-compatible:
// the existing read-only consumers ignore extra keys.
export interface SchoolLeaderAdminData extends SchoolLeaderData {
  id: number;
  phone: string;
  email: string;
}

export interface SchoolEditData {
  moe_code: string;
  name: string;
  short_name: string;
  name_tamil: string;
  address: string;
  postcode: string;
  city: string;
  state: string;
  ppd: string;
  email: string;
  phone: string;
  fax: string;
  gps_lat: number | null;
  gps_lng: number | null;
  gps_verified: boolean;
  enrolment: number;
  preschool_enrolment: number;
  special_enrolment: number;
  teacher_count: number;
  grade: string;
  assistance_type: string;
  skm_eligible: boolean;
  location_type: string;
  session_count: number;
  session_type: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  claimed_at: string | null;
  leaders: SchoolLeaderAdminData[];
}

export interface SubscribeRequest {
  email: string;
  name?: string;
  organisation?: string;
  website?: string;
}

export interface SubscriberResponse {
  email: string;
  name: string;
  organisation: string;
  is_active: boolean;
  subscribed_at: string;
  preferences: Record<string, boolean>;
}

export interface UnsubscribeResponse {
  detail: string;
  email: string;
}

export interface NationalStats {
  total_schools: number;
  total_students: number;
  total_teachers: number;
  total_preschool: number;
  total_special_needs: number;
  states: number;
  constituencies_with_schools: number;
  schools_under_30_students: number;
}

export interface PreferenceUpdate {
  PARLIAMENT_WATCH?: boolean;
  NEWS_WATCH?: boolean;
  MONTHLY_BLAST?: boolean;
}

export interface ConstituencyMention {
  sitting_date: string;
  mp_name: string;
  mp_party: string;
  mention_type: string;
  significance: number | null;
  ai_summary: string;
}

export interface HansardMention {
  id: number;
  sitting_date: string;
  mp_name: string;
  mp_constituency: string;
  mp_party: string;
  mention_type: string;
  significance: number | null;
  sentiment: string;
  ai_summary: string;
  schools: { name: string; moe_code: string }[];
}

export interface SittingBrief {
  id: number;
  sitting_date: string;
  title: string;
  summary_html: string;
  mention_count: number;
  published_at: string | null;
}

export interface Suggestion {
  id: number;
  school: string;
  school_moe_code: string;
  user_name: string;
  school_name: string;
  type: "DATA_CORRECTION" | "PHOTO_UPLOAD" | "NOTE";
  status: "PENDING" | "APPROVED" | "REJECTED";
  field_name: string;
  current_value: string;
  suggested_value: string;
  note: string;
  pending_image_url: string;
  reviewed_by_name: string | null;
  review_note: string;
  points_awarded: number;
  created_at: string;
}

export interface MeetingReport {
  id: number;
  name: string;
  short_name: string;
  term: number;
  session: number;
  year: number;
  start_date: string;
  end_date: string;
  report_html: string;
  executive_summary: string;
  social_post_text: string;
  sitting_count: number;
  total_mentions: number;
  illustration_url: string | null;
  published_at: string | null;
}
