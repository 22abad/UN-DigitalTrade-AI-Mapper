import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { IndicatorMapping, Score } from "../types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function mappingKey(m: IndicatorMapping): string {
  return `${m.indicator}@${m.quote_start}-${m.quote_end}`;
}

export function scoreClass(score: Score): string {
  if (score === 0) return "score-0";
  if (score === 1) return "score-one";
  return "score-half";
}

export function formatScore(score: Score): string {
  if (score === 0) return "0";
  if (score === 1) return "1";
  if (score === 0.25) return "0.25";
  return "0.5";
}

export function formatFeatureValue(v: boolean | number | string): string {
  if (typeof v === "boolean") return v ? "✓" : "✗";
  if (typeof v === "number") return String(v);
  return v;
}

const REGION_MAP: Record<string, string> = {
  Malaysia: "South-East Asia",
  Singapore: "South-East Asia",
  Indonesia: "South-East Asia",
  Thailand: "South-East Asia",
  Vietnam: "South-East Asia",
  Philippines: "South-East Asia",
  Australia: "Pacific",
  "New Zealand": "Pacific",
  India: "South Asia",
  China: "East Asia",
  Japan: "East Asia",
  "South Korea": "East Asia",
};

export function getRegion(economy: string): string {
  return REGION_MAP[economy] ?? "";
}

export function deriveCovName(scope: string): string {
  const s = scope.toLowerCase();
  if (s === "horizontal") return "Cross-cutting";
  return "Sectoral";
}

export const RDTII_CSV_HEADERS = [
  "Pillar_ID",
  "Indicator_ID",
  "Cat_Score",
  "Raw_Score",
  "Act_and_or_practice",
  "Coverage",
  "Impact_or_comments",
  "Timeframe",
  "References",
  "Note",
] as const;

export function mappingsToCsvRows(
  mappings: IndicatorMapping[],
): Record<string, string>[] {
  return mappings.map((m) => ({
    Pillar_ID: m.Pillar_ID || m.pillar_id || `${m.pillar}.0`,
    Indicator_ID: m.Indicator_ID || m.indicator_id || m.indicator,
    Cat_Score: String(m.Cat_Score ?? m.cat_score ?? m.score),
    Raw_Score: String(m.Raw_Score ?? m.raw_score ?? m.score),
    Act_and_or_practice:
      m.Act_and_or_practice ||
      m.act_and_or_practice ||
      m.source_legislation ||
      "",
    Coverage:
      m.Coverage ||
      m.coverage ||
      (m.scope === "unknown"
        ? ""
        : m.scope.charAt(0).toUpperCase() + m.scope.slice(1)),
    Impact_or_comments:
      m.Impact_or_comments || m.impact_or_comments || m.impact || "",
    Timeframe: m.Timeframe || m.timeframe || m.last_update || "",
    References: m.References || m.references || m.source_url || "",
    Note: m.Note || m.note || "",
  }));
}

export function downloadCsv(
  rows: Record<string, string>[],
  filename: string = "rdtii_extraction.csv",
) {
  if (rows.length === 0) return;
  const headers = RDTII_CSV_HEADERS;
  const csvContent = [
    headers.map((h) => `"${h}"`).join(","),
    ...rows.map((r) =>
      headers.map((h) => `"${(r[h] ?? "").replace(/"/g, '""')}"`).join(","),
    ),
  ].join("\n");

  const blob = new Blob(["\ufeff" + csvContent], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
