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
};

export type ReviewDecision = "pending" | "approved" | "rejected";

export type Status = "idle" | "loading" | "ready" | "error";
