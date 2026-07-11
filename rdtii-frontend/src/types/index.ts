export type Pillar = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
export type Score = 0 | 0.25 | 0.5 | 1;
export type Scope = "horizontal" | "sectoral" | "unknown";

export type IndicatorMapping = {
  pillar: Pillar;
  indicator: string;
  score: Score;
  verbatim_quote: string;
  quote_start: number;
  quote_end: number;
  source_legislation: string;
  last_update: string;
  source_url: string;
  scope: Scope;
  coverage: string;
  cluster: string;
  region: string;
  cov_name: string;
  name: string;
  policy_description: string;
  Pillar_ID?: string;
  pillar_id?: string;
  Indicator_ID?: string;
  indicator_id?: string;
  Cat_Score?: number;
  cat_score?: number;
  Raw_Score?: number;
  raw_score?: number;
  Act_and_or_practice?: string;
  act_and_or_practice?: string;
  Coverage?: string;
  Impact_or_comments?: string;
  impact_or_comments?: string;
  Timeframe?: string;
  timeframe?: string;
  References?: string;
  references?: string;
  Note?: string;
  note?: string;
  features: Record<string, boolean | number | string>;
  impact: string;
  requires_human_review: boolean;
  extraction_provider: string;
};

export type RejectedExtraction = {
  reason: string;
  chunk_preview: string;
  raw_output: Record<string, unknown>;
};

export type ExtractionResponse = {
  mappings: IndicatorMapping[];
  rejected: RejectedExtraction[];
  provider: string;
  source_text?: string;
};

export type ReviewDecision = "pending" | "approved" | "rejected";

export type Status = "idle" | "loading" | "ready" | "error";

export type DiscoverySourceMode =
  | "official_first"
  | "official_only"
  | "broad_web";

export type LegalCandidate = {
  id: string;
  country_code: string;
  title: string;
  url: string;
  source_domain: string;
  source_name: string;
  source_grade: "primary" | "secondary" | "unknown";
  document_type: string;
  language: string;
  last_update: string;
  matched_pillars: number[];
  matched_indicators: string[];
  snippet: string;
  confidence: number;
  rank_score: number;
  reasons: string[];
  warnings: string[];
  external_id: string;
  source_adapter: string;
  query: string;
};

export type DiscoverySearchResponse = {
  country_code: string;
  queries: string[];
  candidates: LegalCandidate[];
  diagnostics: {
    adapters_used?: string[];
    raw_hits?: number;
    deduped_hits?: number;
    filtered_low_relevance?: number;
    duration_ms?: number;
    mode?: string;
    source_mode?: DiscoverySourceMode;
    warnings?: string[];
    languages?: string[];
    sources_considered?: number;
    sources_skipped?: string[];
  };
};
