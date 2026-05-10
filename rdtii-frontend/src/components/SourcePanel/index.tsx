import type React from "react";
import { useCallback, useState, useEffect } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { IndicatorMapping, Status } from "../../types";
import { SourceView } from "./SourceView";
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectLabel,
  SelectTrigger, SelectValue, SelectSeparator,
} from "../ui/Select";

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
  availableProviders: string[];
  selectedProvider: string;
  setSelectedProvider: (v: string) => void;
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
  availableProviders,
  selectedProvider,
  setSelectedProvider,
}: SourcePanelProps) {
  const URL_PLACEHOLDERS = [
    "https://www.pdpc.gov.sg/Overview-of-PDPA/The-Legislation/Personal-Data-Protection-Act",
    "https://www.legislation.gov.au/Details/C2022A00010",
    "https://www.pip.org.ph/data-privacy-act/",
    "https://www.moj.gov.cn/pub/sfbcn/publicationData/dataPrivacy.html",
    "https://meity.gov.in/digital-personal-data-protection-act",
  ];

  const [urlPlaceholderIndex, setUrlPlaceholderIndex] = useState(0);
  const [showUrlPlaceholder, setShowUrlPlaceholder] = useState(true);
  const [urlFocused, setUrlFocused] = useState(false);

  useEffect(() => {
    if (urlFocused || sourceUrl) return;
    const interval = setInterval(() => {
      setShowUrlPlaceholder(false);
      setTimeout(() => {
        setUrlPlaceholderIndex((prev) => (prev + 1) % URL_PLACEHOLDERS.length);
        setShowUrlPlaceholder(true);
      }, 400);
    }, 3500);
    return () => clearInterval(interval);
  }, [urlFocused, sourceUrl]);

  const letterVariants = {
    initial: { opacity: 0, filter: "blur(8px)", y: 6 },
    animate: {
      opacity: 1, filter: "blur(0px)", y: 0,
      transition: { opacity: { duration: 0.2 }, filter: { duration: 0.3 }, y: { type: "spring" as const, stiffness: 80, damping: 20 } },
    },
    exit: {
      opacity: 0, filter: "blur(8px)", y: -6,
      transition: { opacity: { duration: 0.15 }, filter: { duration: 0.2 } },
    },
  };

  const textareaRef = useCallback((el: HTMLTextAreaElement | null) => {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, []);
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
          className="group flex items-center justify-center rounded-full text-md h-10 px-6 cursor-pointer transition-all duration-500 bg-[#10B981] text-white"
          style={{ minHeight: 0, border: "none" }}
        >
          <span>
            {status === "loading"
              ? sourceUrl && !text.trim() ? "Crawling..." : "Extracting..."
              : "Run"}
          </span>
          {status !== "loading" && (
            <span className="overflow-hidden w-0 group-hover:w-4 transition-all duration-300 flex items-center justify-center">
              <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17L17 7M17 7H7M17 7V17" />
              </svg>
            </span>
          )}
        </button>
      </div>

      <div className="control-grid">
        <label>
          Country
          <Select value={country} onValueChange={setCountry}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="CHN">China</SelectItem>
              <SelectItem value="IND">India</SelectItem>
              <SelectItem value="SGP">Singapore</SelectItem>
              <SelectItem value="AUS">Australia</SelectItem>
              <SelectItem value="PHL">Philippines</SelectItem>
            </SelectContent>
          </Select>
        </label>
        <label>
          Filter
          <Select value={pillarFilter} onValueChange={setPillarFilter}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All pillars</SelectItem>
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel>Pillar</SelectLabel>
                <SelectItem value="1">P1 · Tariffs and trade defence</SelectItem>
                <SelectItem value="2">P2 · Public procurement</SelectItem>
                <SelectItem value="3">P3 · Foreign direct investment</SelectItem>
                <SelectItem value="4">P4 · Intellectual property rights</SelectItem>
                <SelectItem value="5">P5 · Telecommunications</SelectItem>
                <SelectItem value="6">P6 · Cross-border data flows</SelectItem>
                <SelectItem value="7">P7 · Domestic data protection</SelectItem>
                <SelectItem value="8">P8 · Internet intermediary liability</SelectItem>
                <SelectItem value="9">P9 · Online content access</SelectItem>
                <SelectItem value="10">P10 · Non-technical NTMs</SelectItem>
                <SelectItem value="11">P11 · Standards and procedures</SelectItem>
                <SelectItem value="12">P12 · Online sales and transactions</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </label>
      </div>

      {availableProviders.length > 0 && (
        <div className="stacked">
          <label style={{ display: "block" }}>
            AI Provider
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
              {availableProviders.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setSelectedProvider(p)}
                  className={selectedProvider === p ? "" : "secondary"}
                  style={{ minHeight: 32, padding: "0 14px", fontSize: "0.82rem" }}
                >
                  {PROVIDER_LABELS[p] ?? p}
                </button>
              ))}
            </div>
          </label>
        </div>
      )}

      <label className="stacked">
        Source URL
        <div style={{ position: "relative" }}>
          <input
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            onFocus={() => setUrlFocused(true)}
            onBlur={() => setUrlFocused(false)}
            style={{ position: "relative", zIndex: 1, background: "transparent", fontWeight: "normal" }}
          />
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", padding: "0 12px", pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
            <AnimatePresence mode="wait">
              {showUrlPlaceholder && !urlFocused && !sourceUrl && (
                <motion.span
                  key={urlPlaceholderIndex}
                  style={{ position: "absolute", whiteSpace: "nowrap", color: "#9ca3af", fontSize: "0.92rem", display: "flex", fontWeight: "normal" }}
                  initial={{}}
                  animate={{ transition: { staggerChildren: 0.018 } }}
                  exit={{ transition: { staggerChildren: 0.01, staggerDirection: -1 } }}
                >
                  {URL_PLACEHOLDERS[urlPlaceholderIndex].split("").map((char, i) => (
                    <motion.span key={i} variants={letterVariants} initial="initial" animate="animate" exit="exit" style={{ display: "inline-block" }}>
                      {char === " " ? "\u00A0" : char}
                    </motion.span>
                  ))}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>
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
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = `${e.target.scrollHeight}px`;
              onTextChange(e);
            }}
            placeholder="Paste or crawl legal text to begin..."
          />
        )}
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
