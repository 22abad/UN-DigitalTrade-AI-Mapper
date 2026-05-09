import type React from "react";
import type { IndicatorMapping, Status } from "../../types";
import { SourceView } from "./SourceView";

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

export function SourcePanel({
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
}: SourcePanelProps) {
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
          {status === "loading"
            ? sourceUrl && !text.trim()
              ? "Crawling & Extracting..."
              : "Extracting..."
            : "Run Extraction"}
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
          <select value={pillarFilter} onChange={(e) => setPillarFilter(e.target.value)}>
            <option value="all">All pillars</option>
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

      <div className="stacked text-area-label">
        <div className="source-bar">
          <span>
            {activeMapping
              ? "Audit Highlight (Click to edit text)"
              : "Source text (Editable)"}
          </span>
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
