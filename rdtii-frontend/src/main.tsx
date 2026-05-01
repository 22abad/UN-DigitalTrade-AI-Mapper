import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

type ExtractionResult = {
  title: string;
  last_update: string;
  url: string;
  scope: string;
  provisions: string;
  impact: string;
  requires_human_review: boolean;
};

type ReviewDecision = "pending" | "approved" | "rejected";

const API_URL =
  import.meta.env.VITE_EXTRACT_API_URL ?? "http://localhost:8000/api/extract";

const sampleText = `Article 22. Personal information processors may provide personal information outside the territory only where the conditions prescribed by law are satisfied.

Article 23. Where personal information is provided outside the territory, individuals shall be informed of the overseas recipient, processing purpose, method, and rights procedures.`;

function emptyResult(): ExtractionResult {
  return {
    title: "",
    last_update: "",
    url: "",
    scope: "",
    provisions: "",
    impact: "",
    requires_human_review: true,
  };
}

function App() {
  const [country, setCountry] = React.useState("CHN");
  const [pillar, setPillar] = React.useState("6");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [text, setText] = React.useState(sampleText);
  const [result, setResult] = React.useState<ExtractionResult>(emptyResult());
  const [decision, setDecision] = React.useState<ReviewDecision>("pending");
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState("");

  async function extract() {
    setIsLoading(true);
    setError("");
    setDecision("pending");

    try {
      const form = new FormData();
      form.append("text", text);

      const response = await fetch(API_URL, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        throw new Error(`Extraction failed with status ${response.status}`);
      }

      const data = (await response.json()) as ExtractionResult;
      setResult({
        ...data,
        url: data.url && data.url !== "N/A" ? data.url : sourceUrl,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed");
      setResult(emptyResult());
    } finally {
      setIsLoading(false);
    }
  }

  const confidenceLabel = result.requires_human_review
    ? "Needs review"
    : "Ready for review";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">UN ESCAP RDTII</p>
          <h1>Digital Trade Evidence Workbench</h1>
        </div>
        <div className="status-strip">
          <span>Country {country}</span>
          <span>Pillar {pillar}</span>
          <span className={result.requires_human_review ? "warn" : "ok"}>
            {confidenceLabel}
          </span>
        </div>
      </header>

      <section className="workspace">
        <section className="input-panel" aria-label="Source legal text">
          <div className="panel-header">
            <div>
              <h2>Source</h2>
              <p>Legal text awaiting RDTII pre-categorisation</p>
            </div>
            <button onClick={extract} disabled={isLoading || !text.trim()}>
              {isLoading ? "Extracting..." : "Run Extraction"}
            </button>
          </div>

          <div className="control-grid">
            <label>
              Country
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              >
                <option value="CHN">China</option>
                <option value="IND">India</option>
                <option value="SGP">Singapore</option>
                <option value="AUS">Australia</option>
                <option value="PHL">Philippines</option>
              </select>
            </label>
            <label>
              Pillar
              <select
                value={pillar}
                onChange={(e) => setPillar(e.target.value)}
              >
                <option value="6">Pillar 6: Cross-border data flows</option>
                <option value="7">Pillar 7: Domestic data protection</option>
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

          <label className="stacked text-area-label">
            Extracted legal text
            <textarea value={text} onChange={(e) => setText(e.target.value)} />
          </label>

          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="review-panel" aria-label="Extraction review">
          <div className="panel-header">
            <div>
              <h2>Review</h2>
              <p>Structured output for policy lead validation</p>
            </div>
            <div className="review-actions">
              <button
                className="secondary"
                onClick={() => setDecision("rejected")}
                disabled={!result.provisions}
              >
                Reject
              </button>
              <button
                onClick={() => setDecision("approved")}
                disabled={!result.provisions}
              >
                Approve
              </button>
            </div>
          </div>

          <div className="decision-row">
            <span className={`decision ${decision}`}>{decision}</span>
            <span>
              {result.requires_human_review
                ? "Human check required"
                : "AI pre-check complete"}
            </span>
          </div>

          <Field label="Law or regulation title" value={result.title} />
          <Field label="Last update" value={result.last_update} />
          <Field label="Source URL" value={result.url} />
          <Field label="Scope" value={result.scope} />
          <Field label="Relevant provisions" value={result.provisions} large />
          <Field label="Impact" value={result.impact} large />
        </section>
      </section>
    </main>
  );
}

function Field({
  label,
  value,
  large = false,
}: {
  label: string;
  value: string;
  large?: boolean;
}) {
  return (
    <div className={large ? "field large" : "field"}>
      <span>{label}</span>
      <p>{value || "Awaiting extraction"}</p>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
