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
  dun_name: string | null;
}

export interface Constituency {
  code: string;
  name: string;
  state: string;
  mp_name: string;
  mp_party: string;
  school_count: number;
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
