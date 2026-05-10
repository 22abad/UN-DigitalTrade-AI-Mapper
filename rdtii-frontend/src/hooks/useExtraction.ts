import { useState, useEffect } from "react";
import { API_URL, REVIEW_API_URL, sampleText } from "../lib/constants";
import { mappingKey } from "../lib/utils";
import type {
  ExtractionResponse,
  IndicatorMapping,
  ReviewDecision,
  Status,
} from "../types";

export function useExtraction() {
  const [country, setCountry] = useState("CHN");
  const [pillarFilter, setPillarFilter] = useState("all");
  const [sourceUrl, setSourceUrl] = useState("");
  const [text, setText] = useState(sampleText);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [response, setResponse] = useState<ExtractionResponse | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, ReviewDecision>>({});
  const [showRejected, setShowRejected] = useState(false);
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("gemini");

  useEffect(() => {
    fetch(API_URL.replace("/api/extract", "/health"))
      .then((res) => res.json())
      .then((data) => {
        if (data.available_providers) setAvailableProviders(data.available_providers);
        if (data.active_provider) setSelectedProvider(data.active_provider);
      })
      .catch(() => {});
  }, []);

  const mappings = response?.mappings ?? [];
  const rejected = response?.rejected ?? [];
  const provider = response?.provider ?? "—";
  const activeMapping = mappings.find((m) => mappingKey(m) === activeKey) ?? null;

  const visibleMappings = mappings.filter((m) =>
    pillarFilter === "all" ? true : String(m.pillar) === pillarFilter,
  );

  const pendingCount = mappings.filter(
    (m) => (decisions[mappingKey(m)] ?? "pending") === "pending",
  ).length;

  async function extract() {
    setStatus("loading");
    setError("");

    try {
      const form = new FormData();
      form.append("text", text);
      if (sourceUrl.trim()) form.append("source_url", sourceUrl.trim());
      form.append("provider", selectedProvider);

      const res = await fetch(API_URL, { method: "POST", body: form });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail || `Extraction failed with status ${res.status}`,
        );
      }

      const data = (await res.json()) as ExtractionResponse;

      // Metadata fallback — replace hallucinated URL/date placeholders with real values.
      data.mappings = data.mappings.map((m: IndicatorMapping) => {
        const isHallucinatedUrl =
          !m.source_url ||
          m.source_url.toLowerCase().includes("n/a") ||
          m.source_url.toLowerCase().includes("not specified");
        const isHallucinatedDate =
          !m.last_update ||
          m.last_update.toLowerCase().includes("n/a") ||
          m.last_update.toLowerCase().includes("not specified");

        return {
          ...m,
          source_url: isHallucinatedUrl ? sourceUrl : m.source_url,
          last_update: isHallucinatedDate
            ? new Date().toISOString().split("T")[0]
            : m.last_update,
        };
      });

      setResponse(data);
      setActiveKey(null);
      setDecisions({});
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed");
      setResponse(null);
      setStatus("error");
    }
  }

  function onTextChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    if (response) {
      setResponse(null);
      setActiveKey(null);
      setStatus("idle");
    }
  }

  function selectMapping(key: string) {
    setActiveKey((prev) => (prev === key ? null : key));
  }

  async function setDecision(key: string, d: ReviewDecision) {
    const mapping = mappings.find((m) => mappingKey(m) === key);
    if (!mapping) return;

    setDecisions((prev) => ({ ...prev, [key]: d }));

    if (d === "pending") return;

    try {
      const res = await fetch(REVIEW_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: d, country_code: country, mapping }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail || "Review failed to save to database",
        );
      }
    } catch (err) {
      console.error("Database sync error:", err);
      setError(err instanceof Error ? err.message : "Failed to sync to DB");
    }
  }

  return {
    country, setCountry,
    pillarFilter, setPillarFilter,
    sourceUrl, setSourceUrl,
    text, onTextChange,
    status,
    error,
    provider,
    mappings,
    visibleMappings,
    rejected,
    activeKey, setActiveKey,
    activeMapping,
    decisions,
    pendingCount,
    showRejected, setShowRejected,
    availableProviders,
    selectedProvider, setSelectedProvider,
    extract,
    selectMapping,
    setDecision,
  };
}
