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

export function mappingsToCsvRows(mappings: IndicatorMapping[], country: string): Record<string, string>[] {
  const region = getRegion(country);
  return mappings.map((m) => ({
    country: country || "[PENDING HUMAN REVIEW]",
    "Act.and.or.practice": m.source_legislation || "[PENDING HUMAN REVIEW]",
    Coverage: m.coverage || (m.scope === "horizontal" ? "Cross-cutting" : "Sectoral"),
    Timeframe: m.last_update || "",
    References: m.source_url || "[PENDING HUMAN REVIEW]",
    cluster: m.cluster || "[PENDING HUMAN REVIEW]",
    Region: m.region || region || "[PENDING HUMAN REVIEW]",
    "Cov.Name": m.cov_name || deriveCovName(m.scope),
    name: m.name || "[PENDING HUMAN REVIEW]",
    "policy.description": m.policy_description || "[PENDING HUMAN REVIEW]",
  }));
}

export function downloadCsv(
  rows: Record<string, string>[],
  filename: string = "rdtii_extraction.csv",
) {
  if (rows.length === 0) return;
  const headers = [
    "country",
    "Act.and.or.practice",
    "Coverage",
    "Timeframe",
    "References",
    "cluster",
    "Region",
    "Cov.Name",
    "name",
    "policy.description",
  ];
  const csvContent = [
    headers.map((h) => `"${h}"`).join(","),
    ...rows.map((r) => headers.map((h) => `"${(r[h] ?? "").replace(/"/g, '""')}"`).join(",")),
  ].join("\n");

  const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
