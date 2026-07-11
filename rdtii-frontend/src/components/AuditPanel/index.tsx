import { useCallback } from "react";
import type {
  IndicatorMapping,
  RejectedExtraction,
  ReviewDecision,
  Status,
} from "../../types";
import { AuditBody } from "./AuditBody";
import { RejectedPanel } from "./RejectedPanel";
import { downloadCsv, mappingsToCsvRows } from "../../lib/utils";
import { t } from "../../lib/i18n";

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
  country?: string;
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
  country = "",
}: AuditPanelProps) {
  const handleDownload = useCallback(() => {
    const rows = mappingsToCsvRows(mappings);
    downloadCsv(
      rows,
      `rdtii_extraction_${country || "unknown"}_${Date.now()}.csv`,
    );
  }, [mappings, country]);

  return (
    <section
      className="review-panel self-start flex flex-col max-h-[calc(100vh-40px)]"
      aria-label={t("audit.aria")}
    >
      <div className="panel-header shrink-0">
        <div>
          <h2>{t("audit.title")}</h2>
          <p>{t("audit.description")}</p>
        </div>
        {mappings.length > 0 && (
          <button
            type="button"
            className="secondary text-xs"
            onClick={handleDownload}
            title={t("audit.exportCsvTitle")}
          >
            {t("audit.exportCsv")}
          </button>
        )}
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
