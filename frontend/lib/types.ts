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
  dun_code: string | null;
  dun_name: string | null;
  last_verified: string | null;
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
