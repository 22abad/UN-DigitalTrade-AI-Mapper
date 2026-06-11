import { useState, useEffect, useRef } from "react";
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
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [selectedOllamaModel, setSelectedOllamaModel] = useState("gemma4:12b");
  const [vertexModels, setVertexModels] = useState<string[]>([]);
  const [selectedVertexModel, setSelectedVertexModel] = useState("gemini-2.5-flash");
  const [foundPdfs, setFoundPdfs] = useState<string[]>([]);

  // ── Country auto-detection ──────────────────────────────────────
  const [detectedCountry, setDetectedCountry] = useState<{ code: string; name: string; detected: boolean } | null>(null);
  const detectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function triggerCountryDetect(srcUrl: string, srcText: string) {
    if (detectTimer.current) clearTimeout(detectTimer.current);
    const hasUrl = srcUrl.trim().length > 0;
    const hasText = srcText.trim().length > 80;
    if (!hasUrl && !hasText) return;

    detectTimer.current = setTimeout(async () => {
      try {
        const body = hasUrl
          ? JSON.stringify({ source_url: srcUrl, text: srcText.slice(0, 500) })
          : JSON.stringify({ text: srcText.slice(0, 500) });
        const res = await fetch("/api/detect/country", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.detected && data.code) {
          setDetectedCountry({ code: data.code, name: data.name, detected: true });
          setCountry(data.code);
        } else if (!detectedCountry) {
          // Only clear if user hasn't manually selected
          setDetectedCountry({ code: "", name: "", detected: false });
        }
      } catch { /* network errors — ignore */ }
    }, hasUrl ? 300 : 800);
  }

  // Trigger on initial text
  useEffect(() => {
    if (text.trim().length > 80) {
      triggerCountryDetect(sourceUrl, text);
    }
  }, []);

  useEffect(() => {
    fetch("/health")
      .then((res) => res.json())
      .then((data) => {
        if (data.available_providers) setAvailableProviders(data.available_providers);
        if (data.active_provider) setSelectedProvider(data.active_provider);
      })
      .catch(() => {});
    fetch("/providers/ollama-models")
      .then((res) => res.json())
      .then((data) => {
        if (data.models && data.models.length > 0) {
          setOllamaModels(data.models);
          if (!data.models.includes("gemma4:12b")) {
            setSelectedOllamaModel(data.models[0]);
          }
        }
      })
      .catch(() => {});
    fetch("/providers/vertex-models")
      .then((res) => res.json())
      .then((data) => {
        if (data.models && data.models.length > 0) {
          setVertexModels(data.models);
          if (!data.models.includes("gemini-2.5-flash")) {
            setSelectedVertexModel(data.models[0]);
          }
        }
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
    if (selectedProvider === "ollama") {
      form.append("model", selectedOllamaModel);
    } else if (selectedProvider === "vertex-ai") {
      form.append("model", selectedVertexModel);
    }

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
      if (selectedProvider === "ollama") {
        form.append("model", selectedOllamaModel);
      } else if (selectedProvider === "vertex-ai") {
        form.append("model", selectedVertexModel);
      }

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
    triggerCountryDetect(sourceUrl, e.target.value);
    if (response) {
      setResponse(null);
      setActiveKey(null);
      setStatus("idle");
    }
  }

  function handleSetSourceUrl(v: string) {
    setSourceUrl(v);
    triggerCountryDetect(v, text);
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

    // Prompt for review notes/feedback if approving or rejecting (optional)
    let reviewerNotes = "";
    if (d === "approved" || d === "rejected") {
      if (d === "approved") {
        const notes = window.prompt("Enter optional approval notes or compliance context to save to audit log:");
        if (notes === null) return; // user cancelled the action
        reviewerNotes = notes.trim();
      } else {
        // Rejection quick-select templates (saves time and standardizes agent fine-tuning feedback)
        const promptMsg = 
          "Select a Rejection Reason by typing its NUMBER (1-5), or type your own custom comment:\n\n" +
          "1. [Catalog/Title] This is just a title, section heading, or table of contents, not a substantive policy.\n" +
          "2. [Irrelevant] The extracted quote has no relevance to the selected indicator.\n" +
          "3. [Gov Data] The measure applies only to government/public data, which is excluded under RDTII.\n" +
          "4. [Hallucination] The quote contains hallucinatory, scrambled, or badly translated text.\n" +
          "5. [Outdated] The policy is outdated, repealed, or replaced by a newer regulation.\n\n" +
          "Type number (1-5) or type custom comments:";
          
        const notes = window.prompt(promptMsg);
        if (notes === null) return; // user cancelled the action
        
        const trimmed = notes.trim();
        if (trimmed === "1") {
          reviewerNotes = "This quote is just a title, section heading, or table of contents, not a substantive policy. Do not extract headers or catalog lists.";
        } else if (trimmed === "2") {
          reviewerNotes = "The extracted quote is not relevant to the selected indicator. Only extract provisions directly regulating this specific policy indicator.";
        } else if (trimmed === "3") {
          reviewerNotes = "The measure applies only to government or public data, which is excluded under RDTII guidelines. Do not map public sector internal storage or retention.";
        } else if (trimmed === "4") {
          reviewerNotes = "The quote contains hallucinatory, scrambled, or badly translated text. Please verify exact wording.";
        } else if (trimmed === "5") {
          reviewerNotes = "The policy is outdated, repealed, or has been replaced by a newer regulation. Check for more recent notices.";
        } else {
          reviewerNotes = trimmed; // User's custom comments
        }
      }
    }

    setDecisions((prev) => ({ ...prev, [key]: d }));

    if (d === "pending") return;

    try {
      const res = await fetch(REVIEW_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getStoredToken()}`,
        },
        body: JSON.stringify({ decision: d, country_code: country, mapping, reviewer_notes: reviewerNotes }),
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
    detectedCountry,
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
    ollamaModels, selectedOllamaModel, setSelectedOllamaModel,
    vertexModels, selectedVertexModel, setSelectedVertexModel,
    foundPdfs,
    extract,
    ingestFile,
    selectMapping,
    setDecision,
  };
}
