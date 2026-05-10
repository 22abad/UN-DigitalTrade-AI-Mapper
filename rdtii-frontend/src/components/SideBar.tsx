import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, Plus, Minus } from "lucide-react";
import type { Status } from "../types";

type TopBarProps = {
  country: string;
  provider: string;
  status: Status;
  mappingsCount: number;
  pendingCount: number;
  sourceUrl: string;
  availableProviders: string[];
  selectedProvider: string;
  setSelectedProvider: (v: string) => void;
  onClose: () => void;
};

const PROVIDER_LABELS: Record<string, string> = {
  gemini: "Gemini",
  claude: "Claude",
  openai: "OpenAI",
  deepseek: "DeepSeek",
  groq: "Groq",
  mistral: "Mistral",
  together: "Together AI",
  openrouter: "OpenRouter",
  "llama-3-local": "Llama 3 (Local)",
};

function SubSection({ label, summary, children }: { label: string; summary?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ background: "transparent", border: "none", minHeight: 0, cursor: "pointer", width: "100%", padding: 0, display: "flex", alignItems: "center", justifyContent: "space-between" }}
      >
        <span className="text-xs text-white/40">{label}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {!open && summary && <span className="text-xs font-semibold text-white">{summary}</span>}
          {open && (
            <motion.span
              initial={{ opacity: 0 }} animate={{ opacity: 0.3 }}
              style={{ display: "flex" }}
            >
              <Minus size={10} color="white" />
            </motion.span>
          )}
        </div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="sub"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ height: { type: "spring", stiffness: 300, damping: 30 }, opacity: { duration: 0.15 } }}
            style={{ overflow: "hidden" }}
          >
            <div className="pt-2 space-y-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Section({ label, children, defaultOpen = true }: { label: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-white/10">
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ background: "transparent", border: "none", minHeight: 0, cursor: "pointer", width: "100%", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}
      >
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/30">{label}</p>
        <span style={{ display: "flex", opacity: 0.3 }}>
          {open ? <Minus size={12} color="white" /> : <Plus size={12} color="white" />}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ height: { type: "spring", stiffness: 300, damping: 30 }, opacity: { duration: 0.15 } }}
            style={{ overflow: "hidden" }}
          >
            <div className="px-6 pb-5 space-y-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SideBar({
  country,
  provider,
  status,
  mappingsCount,
  pendingCount,
  sourceUrl,
  availableProviders,
  selectedProvider,
  setSelectedProvider,
  onClose,
}: TopBarProps) {
  const headerStatus =
    status === "loading"
      ? sourceUrl ? "Crawling..." : "Extracting…"
      : status === "error" ? "Error"
      : status === "ready" ? `${mappingsCount} mapping${mappingsCount === 1 ? "" : "s"} · ${pendingCount} pending`
      : "Idle";

  const statusChip =
    status === "error" ? "bg-red-500/20 text-red-300 border-red-500/30"
    : status === "ready" ? "bg-[#10B981]/20 text-[#10B981] border-[#10B981]/30"
    : status === "loading" ? "bg-yellow-400/20 text-yellow-300 border-yellow-400/30"
    : "bg-white/10 text-white/50 border-white/10";

  return (
    <aside className="w-56 shrink-0 h-full flex flex-col bg-[#0c1210] text-white border-r border-white/10">

      {/* Logo + close */}
      <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between">
        <img src="/svg.svg" alt="Sentinel" className="h-6 w-auto brightness-0 invert cursor-pointer" onClick={() => window.location.href = "/"} />
        <button
          onClick={onClose}
          title="Close sidebar"
          style={{ background: "transparent", border: "none", padding: 0, minHeight: 0, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <X size={16} strokeWidth={2} color="white" />
        </button>
      </div>

      {/* Mode */}
      <div className="px-6 py-5 border-b border-white/10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-1">Mode</p>
        <p className="text-sm font-semibold text-white">Evidence Workbench</p>
        <p className="text-[11px] text-white/40 mt-0.5">UN ESCAP DTAM</p>
      </div>

      {/* Session */}
      <Section label="Session">
        <div className="flex justify-between items-center">
          <span className="text-xs text-white/40">Country</span>
          <span className="text-xs font-semibold text-white">{country}</span>
        </div>
        <SubSection
          label="Provider"
          summary={PROVIDER_LABELS[selectedProvider] ?? selectedProvider ?? provider ?? "—"}
        >
          {availableProviders.map((p) => (
            <button
              key={p}
              onClick={() => setSelectedProvider(p)}
              style={{ background: "transparent", border: "none", minHeight: 0, cursor: "pointer", width: "100%", padding: "4px 0", display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <span className={`text-xs ${selectedProvider === p ? "text-[#10B981] font-semibold" : "text-white/50"}`}>
                {PROVIDER_LABELS[p] ?? p}
              </span>
              {selectedProvider === p && (
                <span className="text-[#10B981] text-xs">⎷</span>
              )}
            </button>
          ))}
        </SubSection>
      </Section>

      {/* Status */}
      <Section label="Status">
        <span className={`inline-block text-xs font-semibold px-3 py-1.5 rounded-full border ${statusChip}`}>
          {headerStatus}
        </span>
      </Section>

      {/* History */}
      <Section label="History" defaultOpen={false}>
        <span className={`inline-block text-xs font-semibold px-3 py-1.5 rounded-full border ${statusChip}`}>
          {headerStatus}
        </span>
      </Section>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Back to home */}
      <div className="px-6 py-5 border-t border-white/10">
        <a href="/" className="flex items-center gap-2 text-xs text-white/30 hover:text-white transition-colors">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Home
        </a>
      </div>

    </aside>
  );
}
