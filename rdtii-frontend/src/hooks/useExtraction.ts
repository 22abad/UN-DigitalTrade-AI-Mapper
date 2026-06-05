import { useState, useEffect } from "react";
import { INGEST_API_URL, REVIEW_API_URL, STREAM_API_URL, sampleText } from "../lib/constants";
import { getStoredToken } from "./useAuth";
import { mappingKey } from "../lib/utils";
import type {
  ExtractionResponse,
  IndicatorMapping,
  RejectedExtraction,
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
  const [warning, setWarning] = useState("");
  const [response, setResponse] = useState<ExtractionResponse | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, ReviewDecision>>({});
  const [showRejected, setShowRejected] = useState(false);
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("gemini");
  const [foundPdfs, setFoundPdfs] = useState<string[]>([]);

  useEffect(() => {
    fetch("/health")
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

  function _fixMapping(m: IndicatorMapping, fallbackUrl: string): IndicatorMapping {
    const isHallucinatedUrl =
      !m.source_url ||
      m.source_url.toLowerCase().includes("n/a") ||
      m.source_url.toLowerCase().includes("not specified");
    const isHallucinatedDate =
      !m.last_update ||
      m.last_update.toLowerCase().includes("n/a") ||
      m.last_update.toLowerCase().includes("not specified");
    const isLegislationUrl =
      /^https?:\/\//i.test(m.source_legislation ?? "") ||
      (m.source_legislation ?? "").includes("://");
    return {
      ...m,
      source_url: isHallucinatedUrl ? fallbackUrl : m.source_url,
      last_update: isHallucinatedDate ? new Date().toISOString().split("T")[0] : m.last_update,
      source_legislation: isLegislationUrl ? "" : m.source_legislation,
    };
  }

  async function extract() {
    setStatus("loading");
    setError("");
    setWarning("");
    setResponse(null);
    setFoundPdfs([]);
    setActiveKey(null);
    setDecisions({});

    const form = new FormData();
    form.append("text", text);
    if (sourceUrl.trim()) form.append("source_url", sourceUrl.trim());
    form.append("provider", selectedProvider);

    try {
      const res = await fetch(STREAM_API_URL, {
        method: "POST",
        headers: { Authorization: `Bearer ${getStoredToken()}` },
        body: form,
      });

      if (!res.ok || !res.body) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Extraction failed with status ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let currentEvent = "";
      const collectedMappings: IndicatorMapping[] = [];
      const collectedRejected: RejectedExtraction[] = [];
      let sourceText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const payload = JSON.parse(line.slice(6));

            if (currentEvent === "error") {
              throw new Error(payload.detail ?? "Stream error");
            }

            if (currentEvent === "warning") {
              setWarning(payload.message ?? "");
            }

            if (currentEvent === "found_pdfs") {
              setFoundPdfs(payload.urls ?? []);
            }

            if (currentEvent === "started") {
              if (payload.source_text) {
                sourceText = payload.source_text;
                setText(payload.source_text);
              }
            }

            if (currentEvent === "mapping") {
              const m = _fixMapping(payload as IndicatorMapping, sourceUrl);
              collectedMappings.push(m);
              // Progressive render — derive state from local arrays, never from prev
              // (avoids stale-closure bleed when setResponse(null) hasn't flushed yet)
              setResponse({
                mappings: [...collectedMappings],
                rejected: [...collectedRejected],
                provider: "",
                source_text: sourceText,
              });
            }

            if (currentEvent === "rejected") {
              collectedRejected.push(payload as RejectedExtraction);
              setResponse({
                mappings: [...collectedMappings],
                rejected: [...collectedRejected],
                provider: "",
                source_text: sourceText,
              });
            }

            if (currentEvent === "done") {
              setStatus("ready");
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed");
      setResponse(null);
      setStatus("error");
    }
  }

  async function ingestFile(file: File) {
    setStatus("loading");
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("provider", selectedProvider);

      const res = await fetch(INGEST_API_URL, {
        method: "POST",
        headers: { Authorization: `Bearer ${getStoredToken()}` },
        body: form,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `Ingest failed with status ${res.status}`);
      }

      const data = (await res.json()) as ExtractionResponse;

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
          source_url: isHallucinatedUrl ? "" : m.source_url,
          last_update: isHallucinatedDate ? new Date().toISOString().split("T")[0] : m.last_update,
        };
      });

      if (data.source_text) setText(data.source_text);
      setResponse(data);
      setActiveKey(null);
      setDecisions({});
      setStatus("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "File ingest failed");
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

  function handleSetSourceUrl(v: string) {
    setSourceUrl(v);
    // If the user points to a new URL, clear any previously crawled text so the
    // backend's "crawl if text is empty" path triggers correctly on the next run.
    if (v.trim()) {
      setText("");
      if (response) {
        setResponse(null);
        setActiveKey(null);
        setStatus("idle");
      }
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
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getStoredToken()}`,
        },
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
    warning,
    pillarFilter, setPillarFilter,
    sourceUrl, setSourceUrl: handleSetSourceUrl,
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
    foundPdfs,
    extract,
    ingestFile,
    selectMapping,
    setDecision,
  };
}
