import { useState } from "react";
import { QUOTE_TRUNCATE } from "../../lib/constants";
import { formatFeatureValue, formatScore, scoreClass } from "../../lib/utils";
import type { IndicatorMapping, ReviewDecision } from "../../types";

type MappingCardProps = {
  mapping: IndicatorMapping;
  mappingKeyStr: string;
  active: boolean;
  decision: ReviewDecision;
  onSelect: () => void;
  onDecision: (d: ReviewDecision) => void;
};

export function MappingCard({
  mapping,
  mappingKeyStr,
  active,
  decision,
  onSelect,
  onDecision,
}: MappingCardProps) {
  const [expanded, setExpanded] = useState(false);
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
        "{visibleQuote}"
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

      {mapping.impact ? (
        <p className="impact">
          <strong>Scoring Reason:</strong> {mapping.impact}
        </p>
      ) : null}

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
