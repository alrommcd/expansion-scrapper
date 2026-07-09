// Mirrors export_frontend_data.py's output shapes exactly. If the export
// script's field names change, update here - these are not independently
// invented, they are the contract with the Python engine's static JSON.

export interface City {
  city_id: string;
  city_name: string;
  state: string;
  corridor_count: number;
  has_price_band: boolean;
}

export interface Corridor {
  city_id: string;
  corridor: string;
  eligible: boolean;
  failed_gates: string[];
  fit_score: number | null; // 0-10, display-scaled from the 0-1 composite_score. null = ineligible, never fabricated.
  sub_scores: {
    product_in_band: number;
    demand_adjacent: number;
    clean_title: number;
    comp_density: number;
    resale_velocity: number;
  };
}

export interface Society {
  city_id: string;
  corridor: string;
  society_display: string;
  society_normalized: string;
  supply_depth: number;
  resale_velocity_days: number | null;
  price_consistency_cov: number | null;
  rating: number | null;
  review_count: number | null;
  rating_available: boolean;
  society_fit_score: number | null;
  appears_in_corridors: string[];
  candidate_count: number;
  candidate_listing_ids: number[];
  // Detail enrichment (2026-07-06) - see scoring/society_enrichment.py.
  // detail_available=false means no confident source was found (or
  // GOOGLE_MAPS_API_KEY isn't set) - every other field is null in that case.
  detail_available: boolean;
  official_url: string | null;
  unit_count: string | null;
  possession_status: string | null;
  rera_number: string | null;
  sales_contact: string | null;
  project_description: string | null;
  detail_source: string | null;
  detail_confidence_note: string | null;
}

export interface Broker {
  city_id: string;
  corridor: string;
  agent_display: string;
  agent_normalized: string;
  phone: string | null; // always null today, by design - see scoring/broker_list.py
  company: string | null; // always null today, by design
  listing_count: number;
  broker_activity_score: number;
  sample_detail_url: string | null; // UI traceability only, not part of the score
  // Contact enrichment (2026-07-06) - see scoring/broker_contact_enrichment.py.
  // contact_available=false means no confident source was found (or
  // GOOGLE_MAPS_API_KEY isn't set) - every other field is null in that case.
  contact_available: boolean;
  contact_phone: string | null;
  contact_website: string | null;
  contact_address: string | null;
  contact_source: string | null;
  contact_confidence_note: string | null;
}

export interface AbsenteeCandidate {
  listing_id: number;
  city_id: string;
  corridor: string;
  society: string | null;
  signal_matched: "multi_property_owner" | "never_occupied";
  score: string; // raw match count/marker, NOT the 0-10 style score
  days_since_posted: number | null;
  detail_url: string | null;
  address_recovered: string | null;
  owner_note: string | null;
  traceable: boolean;
  // What actually produced the match (2026-07-06) - see
  // scoring/validated_signals.py. Always a string; falls back to an
  // explicit "detail not retained" message rather than being empty.
  evidence: string;
}

export interface NriDirectoryEntry {
  platform: string;
  group_name: string;
  link: string;
  category: string;
  city_focus: string;
  source_site: string;
}

export interface Stats {
  total_brokers_indexed: number;
  total_absentee_candidates: number;
  total_cities_live: number;
  total_cities_fully_scored: number;
  total_directory_links: number;
  total_corridors_ranked: number;
  total_societies_scored: number;
  total_brokers_contact_resolved: number;
  total_societies_detail_resolved: number;
}

export type ScoreKind = "corridor" | "society" | "broker";
