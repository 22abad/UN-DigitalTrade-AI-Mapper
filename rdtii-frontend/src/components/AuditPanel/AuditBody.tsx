import { mappingKey } from "../../lib/utils";
import type { IndicatorMapping, ReviewDecision, Status } from "../../types";
import { MappingCard } from "./MappingCard";

type AuditBodyProps = {
  status: Status;
  mappings: IndicatorMapping[];
  totalMappings: number;
  activeKey: string | null;
  decisions: Record<string, ReviewDecision>;
  selectMapping: (key: string) => void;
  setDecision: (key: string, d: ReviewDecision) => void;
};

export function AuditBody({
  status,
  mappings,
  totalMappings,
  activeKey,
  decisions,
  selectMapping,
  setDecision,
}: AuditBodyProps) {
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
