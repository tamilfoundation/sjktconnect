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
  image_url: string;
  source: "SATELLITE" | "PLACES" | "STREET_VIEW" | "MANUAL";
  is_primary: boolean;
  attribution: string;
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
  schools: School[];
  scorecard: Scorecard | null;
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

export interface MagicLinkResponse {
  message: string;
  school_name: string;
}

export interface AuthUser {
  school_moe_code: string;
  school_name: string;
  email: string;
  name: string;
  role: string;
  verified_at: string;
}

export interface ApiError {
  error: string;
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
  email: string;
  phone: string;
  fax: string;
  gps_lat: number | null;
  gps_lng: number | null;
  enrolment: number;
  preschool_enrolment: number;
  special_enrolment: number;
  teacher_count: number;
  session_count: number;
  session_type: string;
  last_verified: string | null;
  verified_by: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
}

export interface SchoolConfirmResponse {
  message: string;
  last_verified: string;
  verified_by: string;
}

export interface SubscribeRequest {
  email: string;
  name?: string;
  organisation?: string;
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

export interface SittingBrief {
  id: number;
  sitting_date: string;
  title: string;
  summary_html: string;
  mention_count: number;
  published_at: string | null;
}
