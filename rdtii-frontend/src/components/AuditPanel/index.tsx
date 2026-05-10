import type { IndicatorMapping, RejectedExtraction, ReviewDecision, Status } from "../../types";
import { AuditBody } from "./AuditBody";
import { RejectedPanel } from "./RejectedPanel";

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

export function AuditPanel({
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
}: AuditPanelProps) {
  return (
    <section className="review-panel self-start flex flex-col max-h-[calc(100vh-40px)]" aria-label="Audit view">
      <div className="panel-header shrink-0">
        <div>
          <h2>Audit</h2>
          <p>
            Indicator mappings extracted from source. Click a card to highlight
            its quote on the left.
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
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
      </div>
    </section>
  );
}
