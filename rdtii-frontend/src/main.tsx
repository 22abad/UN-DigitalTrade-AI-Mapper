import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

// ── Types matching the backend /api/extract response (RDTII 2.1) ─────────

type Pillar = 6 | 7;
type Score = 0 | 0.25 | 0.5 | 1;
type Scope = "horizontal" | "sectoral" | "unknown";

type IndicatorMapping = {
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

type RejectedExtraction = {
  reason: string;
  chunk_preview: string;
  raw_output: Record<string, unknown>;
};

type ExtractionResponse = {
  mappings: IndicatorMapping[];
  rejected: RejectedExtraction[];
  provider: string;
};

type ReviewDecision = "pending" | "approved" | "rejected";

type Status = "idle" | "loading" | "ready" | "error";

const API_URL =
  import.meta.env.VITE_EXTRACT_API_URL ?? "http://localhost:8000/api/extract";

const REVIEW_API_URL =
  import.meta.env.VITE_REVIEW_API_URL ?? "http://localhost:8000/api/mappings/review";

const QUOTE_TRUNCATE = 280;

const sampleText = `Article 22. Personal information processors may provide personal information outside the territory only where the conditions prescribed by law are satisfied.

Article 23. Where personal information is provided outside the territory, individuals shall be informed of the overseas recipient, processing purpose, method, and rights procedures.`;

// Composite key so cards survive re-extracts where indicator can repeat.
function mappingKey(m: IndicatorMapping): string {
  return `${m.indicator}@${m.quote_start}-${m.quote_end}`;
}

function scoreClass(score: Score): string {
  if (score === 0) return "score-0";
  if (score === 1) return "score-one";
  return "score-half";
}

function formatScore(score: Score): string {
  if (score === 0) return "0";
  if (score === 1) return "1";
  if (score === 0.25) return "0.25";
  return "0.5";
}

function formatFeatureValue(v: boolean | number | string): string {
  if (typeof v === "boolean") return v ? "✓" : "✗";
  if (typeof v === "number") return String(v);
  return v;
}

// ── App ──────────────────────────────────────────────────────────────────

function App() {
  const [country, setCountry] = React.useState("CHN");
  const [pillarFilter, setPillarFilter] = React.useState("all");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [text, setText] = React.useState(sampleText);
  const [status, setStatus] = React.useState<Status>("idle");
  const [error, setError] = React.useState("");
  const [response, setResponse] = React.useState<ExtractionResponse | null>(
    null,
  );
  const [activeKey, setActiveKey] = React.useState<string | null>(null);
  const [decisions, setDecisions] = React.useState<
    Record<string, ReviewDecision>
  >({});
  const [showRejected, setShowRejected] = React.useState(false);

  const [availableProviders, setAvailableProviders] = React.useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = React.useState<string>("gemini");

  React.useEffect(() => {
    fetch(API_URL.replace("/api/extract", "/health"))
      .then((res) => res.json())
      .then((data) => {
        if (data.available_providers) {
          setAvailableProviders(data.available_providers);
        }
        if (data.active_provider) {
          setSelectedProvider(data.active_provider);
        }
      })
      .catch((err) => console.error("Failed to fetch health/providers", err));
  }, []);

  const sourceRef = React.useRef<HTMLDivElement>(null);

  const mappings = response?.mappings ?? [];
  const rejected = response?.rejected ?? [];
  const activeMapping =
    mappings.find((m) => mappingKey(m) === activeKey) ?? null;
  const provider = response?.provider ?? "—";

  // Re-scroll the highlight into view whenever the active mapping changes.
  React.useEffect(() => {
    if (!activeMapping || !sourceRef.current) return;
    const mark = sourceRef.current.querySelector("mark");
    if (mark) {
      mark.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [activeKey, activeMapping]);

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
        throw new Error(errorData.detail || `Extraction failed with status ${res.status}`);
      }

      const data = (await res.json()) as ExtractionResponse;

      // Task 1: metadata fallback (anti-hallucination) | 任务 1：元数据兜底（防幻觉）
      data.mappings = data.mappings.map((m) => {
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

    // Optimistically update UI | 乐观更新 UI
    setDecisions((prev) => ({ ...prev, [key]: d }));

    if (d === "pending") return;

    // Task 1: Sync to Backend | 任务 1：同步到后端
    try {
      const res = await fetch(REVIEW_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: d,
          country_code: country,
          mapping: mapping,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Review failed to save to database");
      }
      console.log(`[DB Sync] ${d} decision persisted for ${key}`);
    } catch (err) {
      console.error("Database sync error:", err);
      setError(err instanceof Error ? err.message : "Failed to sync to DB");
    }
  }

  const visibleMappings = mappings.filter((m) =>
    pillarFilter === "all" ? true : String(m.pillar) === pillarFilter,
  );

  const pendingCount = mappings.filter(
    (m) => (decisions[mappingKey(m)] ?? "pending") === "pending",
  ).length;
  const headerStatus =
    status === "loading"
      ? (sourceUrl && !text.trim() ? "Crawling..." : "Extracting…")
      : status === "error"
        ? "Error"
        : status === "ready"
          ? `${mappings.length} mapping${mappings.length === 1 ? "" : "s"} · ${pendingCount} pending`
          : "Idle";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">UN ESCAP RDTII</p>
          <h1>Digital Trade Evidence Workbench</h1>
        </div>
        <div className="status-strip">
          <span>Country {country}</span>
          <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
            {availableProviders.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <span className={status === "error" ? "warn" : "ok"}>
            {headerStatus}
          </span>
        </div>
      </header>

      <section className="workspace">
        <SourcePanel
          sourceRef={sourceRef}
          country={country}
          setCountry={setCountry}
          pillarFilter={pillarFilter}
          setPillarFilter={setPillarFilter}
          sourceUrl={sourceUrl}
          setSourceUrl={setSourceUrl}
          text={text}
          onTextChange={onTextChange}
          activeMapping={activeMapping}
          setActiveKey={setActiveKey}
          extract={extract}
          status={status}
          error={error}
        />

        <AuditPanel
          status={status}
          mappings={visibleMappings}
          totalMappings={mappings.length}
          activeKey={activeKey}
          decisions={decisions}
          selectMapping={selectMapping}
          setDecision={setDecision}
          rejected={rejected}
          showRejected={showRejected}
          setShowRejected={setShowRejected}
        />
      </section>
    </main>
  );
}

// ── Source panel (left) ──────────────────────────────────────────────────

type SourcePanelProps = {
  sourceRef: React.RefObject<HTMLDivElement>;
  country: string;
  setCountry: (v: string) => void;
  pillarFilter: string;
  setPillarFilter: (v: string) => void;
  sourceUrl: string;
  setSourceUrl: (v: string) => void;
  text: string;
  onTextChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  activeMapping: IndicatorMapping | null;
  setActiveKey: (key: string | null) => void;
  extract: () => void;
  status: Status;
  error: string;
};

function SourcePanel(props: SourcePanelProps) {
  const {
    sourceRef,
    country,
    setCountry,
    pillarFilter,
    setPillarFilter,
    sourceUrl,
    setSourceUrl,
    text,
    onTextChange,
    activeMapping,
    setActiveKey,
    extract,
    status,
    error,
  } = props;

  return (
    <section className="input-panel" aria-label="Source legal text">
      <div className="panel-header">
        <div>
          <h2>Source</h2>
          <p>Legal text awaiting RDTII pre-categorisation</p>
        </div>
        <button
          onClick={extract}
          disabled={status === "loading" || (!text.trim() && !sourceUrl.trim())}
        >
          {status === "loading" ? (
            sourceUrl && !text.trim() ? "Crawling & Extracting..." : "Extracting..."
          ) : (
            "Run Extraction"
          )}
        </button>
      </div>

      <div className="control-grid">
        <label>
          Country
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="CHN">China</option>
            <option value="IND">India</option>
            <option value="SGP">Singapore</option>
            <option value="AUS">Australia</option>
            <option value="PHL">Philippines</option>
          </select>
        </label>
        <label>
          Filter
          <select
            value={pillarFilter}
            onChange={(e) => setPillarFilter(e.target.value)}
          >
            <option value="all">All pillars</option>
            <option value="1">Pillar 1: Tariffs and trade defence</option>
            <option value="2">Pillar 2: Public procurement</option>
            <option value="3">Pillar 3: Foreign direct investment</option>
            <option value="4">Pillar 4: Intellectual property rights</option>
            <option value="5">Pillar 5: Telecommunications</option>
            <option value="6">Pillar 6: Cross-border data flows</option>
            <option value="7">Pillar 7: Domestic data protection</option>
            <option value="8">Pillar 8: Internet intermediary liability</option>
            <option value="9">Pillar 9: Online content access</option>
            <option value="10">Pillar 10: Non-technical NTMs</option>
            <option value="11">Pillar 11: Standards and procedures</option>
            <option value="12">Pillar 12: Online sales and transactions</option>
          </select>
        </label>
      </div>

      <label className="stacked">
        Source URL
        <input
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="https://official-source.example/law"
        />
      </label>

      <div className="stacked text-area-label">
        <div className="source-bar">
          <span>{activeMapping ? "Audit Highlight (Click to edit text)" : "Source text (Editable)"}</span>
        </div>
        
        {activeMapping ? (
          <SourceView
            text={text}
            activeMapping={activeMapping}
            sourceRef={sourceRef}
            onClick={() => setActiveKey(null)}
          />
        ) : (
          <textarea 
            value={text} 
            onChange={onTextChange} 
            placeholder="Paste or crawl legal text to begin..."
          />
        )}
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}

function SourceView({
  text,
  activeMapping,
  sourceRef,
  onClick,
}: {
  text: string;
  activeMapping: IndicatorMapping | null;
  sourceRef: React.RefObject<HTMLDivElement>;
  onClick?: () => void;
}) {
  if (!activeMapping) {
    return (
      <div 
        ref={sourceRef} 
        className="source-view" 
        tabIndex={0}
        onClick={onClick}
      >
        {text}
      </div>
    );
  }

  const start = Math.max(0, Math.min(activeMapping.quote_start, text.length));
  const end = Math.max(start, Math.min(activeMapping.quote_end, text.length));

  // Defensive: if the offsets don't actually frame a substring in the
  // current text (e.g. the user edited), fall back to plain text.
  if (start === end) {
    return (
      <div 
        ref={sourceRef} 
        className="source-view" 
        tabIndex={0}
        onClick={onClick}
      >
        {text}
      </div>
    );
  }

  const before = text.slice(0, start);
  const middle = text.slice(start, end);
  const after = text.slice(end);

  return (
    <div 
      ref={sourceRef} 
      className="source-view active-highlight" 
      tabIndex={0}
      onClick={onClick}
      title="Click to switch back to edit mode"
    >
      {before}
      <mark className={`mark ${scoreClass(activeMapping.score)}-mark`}>
        {middle}
      </mark>
      {after}
    </div>
  );
}

// ── Audit panel (right) ──────────────────────────────────────────────────

type AuditPanelProps = {
  status: Status;
  mappings: IndicatorMapping[];
  totalMappings: number;
  activeKey: string | null;
  decisions: Record<string, ReviewDecision>;
  selectMapping: (key: string) => void;
  setDecision: (key: string, d: ReviewDecision) => void;
  rejected: RejectedExtraction[];
  showRejected: boolean;
  setShowRejected: (v: boolean) => void;
};

function AuditPanel(props: AuditPanelProps) {
  const {
    status,
    mappings,
    totalMappings,
    activeKey,
    decisions,
    selectMapping,
    setDecision,
    rejected,
    showRejected,
    setShowRejected,
  } = props;

  return (
    <section className="review-panel" aria-label="Audit view">
      <div className="panel-header">
        <div>
          <h2>Audit</h2>
          <p>
            Indicator mappings extracted from source. Click a card to highlight
            its quote on the left.
          </p>
        </div>
      </div>

      <AuditBody
        status={status}
        mappings={mappings}
        totalMappings={totalMappings}
        activeKey={activeKey}
        decisions={decisions}
        selectMapping={selectMapping}
        setDecision={setDecision}
      />

      {rejected.length > 0 && (
        <RejectedPanel
          rejected={rejected}
          open={showRejected}
          setOpen={setShowRejected}
        />
      )}
    </section>
  );
}

function AuditBody({
  status,
  mappings,
  totalMappings,
  activeKey,
  decisions,
  selectMapping,
  setDecision,
}: {
  status: Status;
  mappings: IndicatorMapping[];
  totalMappings: number;
  activeKey: string | null;
  decisions: Record<string, ReviewDecision>;
  selectMapping: (key: string) => void;
  setDecision: (key: string, d: ReviewDecision) => void;
}) {
  if (status === "idle") {
    return (
      <p className="empty-state">
        Run extraction on the source text to surface RDTII indicator mappings.
      </p>
    );
  }

  if (status === "loading") {
    return <p className="empty-state">Extracting mappings…</p>;
  }

  if (status === "error") {
    return (
      <p className="empty-state error-state">
        Extraction failed. See message in the source panel.
      </p>
    );
  }

  if (mappings.length === 0) {
    return (
      <p className="empty-state">
        {totalMappings === 0
          ? "No mappings produced for this text. Try a different excerpt or check the rejected log below."
          : "No mappings match the current pillar filter."}
      </p>
    );
  }

  return (
    <ul className="mapping-list">
      {mappings.map((m) => {
        const key = mappingKey(m);
        return (
          <MappingCard
            key={key}
            mapping={m}
            mappingKeyStr={key}
            active={key === activeKey}
            decision={decisions[key] ?? "pending"}
            onSelect={() => selectMapping(key)}
            onDecision={(d) => setDecision(key, d)}
          />
        );
      })}
    </ul>
  );
}

// ── Mapping card ─────────────────────────────────────────────────────────

function MappingCard({
  mapping,
  mappingKeyStr,
  active,
  decision,
  onSelect,
  onDecision,
}: {
  mapping: IndicatorMapping;
  mappingKeyStr: string;
  active: boolean;
  decision: ReviewDecision;
  onSelect: () => void;
  onDecision: (d: ReviewDecision) => void;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const featureEntries = Object.entries(mapping.features);

  const quoteIsLong = mapping.verbatim_quote.length > QUOTE_TRUNCATE;
  const visibleQuote =
    quoteIsLong && !expanded
      ? `${mapping.verbatim_quote.slice(0, QUOTE_TRUNCATE)}…`
      : mapping.verbatim_quote;

  return (
    <li
      className={`mapping-card ${active ? "active-mapping" : ""} decision-${decision}`}
      onClick={onSelect}
      onKeyDown={(e) => {
        // Only handle when the LI itself is focused, not when the event
        // bubbles up from a nested button / link / show-more control.
        // Without this guard, keyboard-activating Approve / Reject / Source
        // also toggles the card selection, which is unexpected.
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
      aria-pressed={active}
      aria-label={`Mapping ${mapping.indicator}, score ${formatScore(mapping.score)}`}
      data-testid={`mapping-card-${mappingKeyStr}`}
    >
      <div className="card-row">
        <span className="indicator-badge">
          P{mapping.pillar} · {mapping.indicator}
        </span>
        <span className={`score-badge ${scoreClass(mapping.score)}`}>
          {formatScore(mapping.score)}
        </span>
      </div>

      <div className="card-titles">
        <h3>{mapping.source_legislation || "Untitled legislation"}</h3>
        <p className="muted">
          {mapping.last_update || "Date unknown"}
          {mapping.scope !== "unknown" ? ` · ${mapping.scope}` : null}
        </p>
      </div>

      <blockquote className="quote">
        “{visibleQuote}”
        {quoteIsLong ? (
          <button
            type="button"
            className="link-button"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
          >
            {expanded ? "show less" : "show more"}
          </button>
        ) : null}
      </blockquote>

      {featureEntries.length > 0 ? (
        <div className="feature-row">
          {featureEntries.map(([k, v]) => (
            <span key={k} className="feature-chip">
              <span className="chip-key">{k}</span>
              <span className="chip-val">{formatFeatureValue(v)}</span>
            </span>
          ))}
        </div>
      ) : null}

      {mapping.impact ? <p className="impact"><strong>Scoring Reason:</strong> {mapping.impact}</p> : null}

      <div className="card-footer">
        <div className="card-footer-left">
          {mapping.source_url ? (
            <a
              href={mapping.source_url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              Source ↗
            </a>
          ) : (
            <span className="muted">No source URL</span>
          )}
          {mapping.requires_human_review ? (
            <span className="review-flag">Needs review</span>
          ) : null}
        </div>
        <span className="muted small">
          via {mapping.extraction_provider || "unknown"}
        </span>
      </div>

      <div className="card-actions">
        <button
          type="button"
          className={`secondary ${decision === "rejected" ? "active-reject" : ""}`}
          onClick={(e) => {
            e.stopPropagation();
            onDecision(decision === "rejected" ? "pending" : "rejected");
          }}
        >
          Reject
        </button>
        <button
          type="button"
          className={decision === "approved" ? "active-approve" : ""}
          onClick={(e) => {
            e.stopPropagation();
            onDecision(decision === "approved" ? "pending" : "approved");
          }}
        >
          Approve
        </button>
      </div>
    </li>
  );
}

// ── Rejected panel ───────────────────────────────────────────────────────

function RejectedPanel({
  rejected,
  open,
  setOpen,
}: {
  rejected: RejectedExtraction[];
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  return (
    <details
      className="rejected-panel"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary>Rejected extractions ({rejected.length})</summary>
      <ul>
        {rejected.map((r, i) => (
          <li key={i} className="rejected-item">
            <div className="rejected-reason">{r.reason}</div>
            {r.chunk_preview ? (
              <pre className="rejected-preview">{r.chunk_preview}</pre>
            ) : null}
          </li>
        ))}
      </ul>
    </details>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
