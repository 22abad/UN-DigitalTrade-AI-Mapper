import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FETCH_TEXT_API_URL } from "../../lib/constants";
import { getStoredToken } from "../../hooks/useAuth";
import { AuditPanel } from "../../components/AuditPanel";
import { SourcePanel } from "../../components/SourcePanel";
import { FoundPdfsPanel } from "../../components/SourcePanel/FoundPdfsPanel";
import { SideBar } from "../../components/SideBar";
import { useExtraction } from "../../hooks/useExtraction";
import ColorBends from "../../components/ColorBends/ColorBends";
import { motion, AnimatePresence } from "motion/react";
import { Plus, Menu, X, Home, Map, User } from "lucide-react";
import { GooeyFilter } from "../../components/ui/gooey-filter";

export function WorkbenchPage() {
  const navigate = useNavigate();
  const sourceRef = useRef<HTMLDivElement>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [fetchingPdf, setFetchingPdf] = useState(false);
  const {
    country, setCountry,
    detectedCountry,
    pillarFilter, setPillarFilter,
    sourceUrl, setSourceUrl,
    text, onTextChange,
    status,
    error,
    warning,
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
    <div className="flex overflow-hidden" style={{ height: "100dvh" }}>

      {/* Full-page background */}
      <div className="fixed inset-0 -z-10" style={{ height: "100dvh" }}>
        <ColorBends colors={["#0d3326", "#072418"]} speed={0.15} intensity={1.2} noise={0.1} frequency={0.8} />
      </div>

      <div className="fixed inset-0 -z-10 bg-black/20" style={{ height: "100dvh" }} />

      <div
        className="fixed inset-0 -z-10 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0, 80, 63, 0.20) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 80, 63, 0.20) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

       

      {/* Left sidebar — overlay drawer */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              key="sidebar-backdrop"
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              key="sidebar"
              className="fixed left-0 top-0 bottom-0 z-50"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 32 }}
              style={{ overflow: "hidden" }}
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
                ollamaModels={ollamaModels}
                selectedOllamaModel={selectedOllamaModel}
                setSelectedOllamaModel={setSelectedOllamaModel}
                onClose={() => setSidebarOpen(false)}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Sidebar toggle button */}
      {!sidebarOpen && (
        <div className="fixed left-4 top-4 w-12 h-12 z-50 group">
          <button
            onClick={() => setSidebarOpen(true)}
            title="Open sidebar"
            className="hidden md:flex opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{ width: 48, height: 48, minHeight: 0, borderRadius: "50%", background: "#0c1210", border: "1px solid rgba(255,255,255,0.1)", color: "white", cursor: "pointer", alignItems: "center", justifyContent: "center", padding: 0 }}
          >
            <Plus size={20} color="white" />
          </button>
          <button
            onClick={() => setSidebarOpen(true)}
            title="Open sidebar"
            className="flex md:hidden"
            style={{ width: 48, height: 48, minHeight: 0, background: "transparent", border: "none", color: "white", cursor: "pointer", alignItems: "center", justifyContent: "center", padding: 0 }}
          >
            <Plus size={22} color="white" strokeWidth={1.5} />
          </button>
        </div>
      )}

      {/* Gooey Nav Menu */}
      <GooeyFilter id="gooey-nav-menu" strength={5} />
      <div
        className="fixed top-4 right-4 z-50"
        style={{ filter: "url(#gooey-nav-menu)" }}
      >
        <AnimatePresence>
          {menuOpen && [
            { icon: Home, key: "home", onClick: () => { setMenuOpen(false); navigate("/"); } },
            { icon: Map, key: "workbench", onClick: () => { setMenuOpen(false); navigate("/mapsearch"); } },
            { icon: User, key: "profile", onClick: () => {} },
          ].map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.button
                key={item.key}
                className="absolute w-12 h-12 rounded-full flex items-center justify-center"
                style={{ right: 0, top: 0 }}
                initial={{ x: 0, opacity: 0 }}
                animate={{ y: (i + 1) * 46, opacity: 1 }}
                exit={{ y: 0, opacity: 0, transition: { delay: (3 - i) * 0.04, duration: 0.3, type: "spring", bounce: 0 } }}
                transition={{ delay: i * 0.04, duration: 0.35, type: "spring", bounce: 0 }}
                onClick={item.onClick}
              >
                <div className="absolute inset-0 rounded-full" style={{ background: "#1a2e26" }} />
                <motion.div
                  className="relative z-10"
                  key={item.key}
                  initial={{ opacity: 0, filter: "blur(10px)" }}
                  animate={{ opacity: 0.7, filter: "blur(0px)" }}
                  whileHover={{ opacity: 1 }}
                  exit={{ opacity: 0, filter: "blur(10px)" }}
                  transition={{ delay: i * 0.04, duration: 0.15 }}
                >
                  <Icon size={18} color="white" />
                </motion.div>
              </motion.button>
            );
          })}
        </AnimatePresence>

        <motion.button
          className="relative w-12 h-12 rounded-full flex items-center justify-center"
          style={{ background: "#1a2e26" }}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <AnimatePresence mode="wait">
            {menuOpen ? (
              <motion.div
                key="close"
                initial={{ opacity: 0, filter: "blur(10px)" }}
                animate={{ opacity: 0.7, filter: "blur(0px)" }}
                whileHover={{ opacity: 1 }}
                exit={{ opacity: 0, filter: "blur(10px)" }}
                transition={{ duration: 0.15 }}
              >
                <X size={18} className="text-white" />
              </motion.div>
            ) : (
              <motion.div
                key="menu"
                initial={{ opacity: 0, filter: "blur(10px)" }}
                animate={{ opacity: 0.7, filter: "blur(0px)" }}
                whileHover={{ opacity: 1 }}
                exit={{ opacity: 0, filter: "blur(10px)" }}
                transition={{ duration: 0.15 }}
              >
                <Menu size={18} className="text-white" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Main workspace */}
      <main className="flex-1 overflow-auto px-5 pb-8 pt-12">
        <section className="workspace h-full">

          <div className="flex flex-col gap-4 min-w-0 self-start">
            <SourcePanel
              sourceRef={sourceRef}
              country={country}
              setCountry={setCountry}
              detectedCountry={detectedCountry}
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
              warning={warning}
              availableProviders={availableProviders}
              selectedProvider={selectedProvider}
              setSelectedProvider={setSelectedProvider}
            />
            <AnimatePresence>
              {foundPdfs.length > 0 && (
                <FoundPdfsPanel
                  urls={foundPdfs}
                  loading={fetchingPdf}
                  onSelect={async (url) => {
                    setFetchingPdf(true);
                    try {
                      const form = new FormData();
                      form.append("source_url", url);
                      const res = await fetch(FETCH_TEXT_API_URL, {
                        method: "POST",
                        headers: { Authorization: `Bearer ${getStoredToken()}` },
                        body: form,
                      });
                      const data = await res.json();
                      if (data.text) {
                        setSourceUrl(url);
                        onTextChange({ target: { value: data.text } } as React.ChangeEvent<HTMLTextAreaElement>);
                      }
                    } finally {
                      setFetchingPdf(false);
                    }
                  }}
                />
              )}
            </AnimatePresence>
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
            country={country}
          />

        </section>
      </main>

    </div>
  );
}
