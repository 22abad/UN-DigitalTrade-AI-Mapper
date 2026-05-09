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
