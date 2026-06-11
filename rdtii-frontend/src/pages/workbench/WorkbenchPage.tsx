import { useEffect, useRef, useState } from "react";
import { AuditPanel } from "../../components/AuditPanel";
import { SourcePanel } from "../../components/SourcePanel";
import { SideBar } from "../../components/SideBar";
import { useExtraction } from "../../hooks/useExtraction";
import ColorBends from "../../components/ColorBends/ColorBends";
import { AIChatInput } from "../../components/Workbench/ChatInput";
import { motion, AnimatePresence } from "motion/react";
import { Plus } from "lucide-react";

export function WorkbenchPage() {
  const sourceRef = useRef<HTMLDivElement>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
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
    availableProviders,
    selectedProvider, setSelectedProvider,
    ocrMode, setOcrMode,
    foundPdfs,
    extract,
    selectMapping,
    setDecision,
  } = useExtraction();

  useEffect(() => {
    if (!activeMapping || !sourceRef.current) return;
    const mark = sourceRef.current.querySelector("mark");
    if (mark) mark.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeKey, activeMapping]);

  return (
    <div className="flex h-screen overflow-hidden">

      {/* Full-page background */}
      <div className="fixed inset-0 -z-10">
        <ColorBends colors={["#0d3326", "#072418"]} speed={0.15} intensity={1.2} noise={0.1} frequency={0.8} />
      </div>

      <div className="fixed inset-0 -z-10 bg-black/20" />

      <div
        className="fixed inset-0 -z-10 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0, 80, 63, 0.20) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 80, 63, 0.20) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

       

      {/* Left sidebar */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.div
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 224, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            style={{ overflow: "hidden", flexShrink: 0 }}
          >
            <SideBar
              country={country}
              provider={provider}
              status={status}
              mappingsCount={mappings.length}
              pendingCount={pendingCount}
              sourceUrl={sourceUrl}
              availableProviders={availableProviders}
              selectedProvider={selectedProvider}
              setSelectedProvider={setSelectedProvider}
              onClose={() => setSidebarOpen(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sidebar toggle button — shown when closed */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          title="Open sidebar"
          style={{ position: "fixed", left: 12, top: 12, zIndex: 50, width: 32, height: 32, minHeight: 0, borderRadius: 8, background: "#0c1210", border: "1px solid rgba(255,255,255,0.1)", color: "white", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: 0 }}
        >
          <Plus size={15} color="white" />
        </button>
      )}

      {/* Main workspace */}
      <main className="flex-1 overflow-auto p-5">
        <section className="workspace h-full">

          <div className="flex flex-col gap-4 min-w-0 self-start">
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
              availableProviders={availableProviders}
              selectedProvider={selectedProvider}
              setSelectedProvider={setSelectedProvider}
              ocrMode={ocrMode}
              setOcrMode={setOcrMode}
            />
            <AIChatInput />
          </div>

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

    </div>
  );
}
