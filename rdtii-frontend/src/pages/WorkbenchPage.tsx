import { useEffect, useRef } from "react";
import { AuditPanel } from "../components/AuditPanel";
import { SourcePanel } from "../components/SourcePanel";
import { TopBar } from "../components/TopBar";
import { useExtraction } from "../hooks/useExtraction";

export function WorkbenchPage() {
  const sourceRef = useRef<HTMLDivElement>(null);
  const {
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
    extract,
    selectMapping,
    setDecision,
  } = useExtraction();

  // Scroll highlighted quote into view when the active mapping changes.
  useEffect(() => {
    if (!activeMapping || !sourceRef.current) return;
    const mark = sourceRef.current.querySelector("mark");
    if (mark) mark.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeKey, activeMapping]);

  return (
    <main className="app-shell">
      <TopBar
        country={country}
        provider={provider}
        status={status}
        mappingsCount={mappings.length}
        pendingCount={pendingCount}
        sourceUrl={sourceUrl}
      />

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