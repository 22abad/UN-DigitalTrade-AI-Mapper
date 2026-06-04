import { useState, useEffect, useRef } from "react";
import { getStoredToken } from "../../hooks/useAuth";
import { Lightbulb, Mic, Globe, Paperclip, Send, X } from "lucide-react";
import { AnimatePresence, motion, type Variants } from "motion/react";

const PLACEHOLDERS = [
  "Summarise the cross-border data flow obligations...",
  "Which clauses relate to Pillar 6 indicators?",
  "Extract consent requirements from this text...",
  "Compare this law against RDTII 2.1 standards...",
  "Find data localisation provisions in the source...",
  "Identify breach notification requirements...",
];

const TEXT_SUB_INPUTS = [
  { key: "role", label: "Role", placeholder: "e.g. Legal analyst, Policy researcher..." },
  { key: "context", label: "Context", placeholder: "e.g. Reviewing Singapore's PDPA amendments..." },
];

const CARD_H = 56;
const CARD_GAP = 10;

function extColor(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "pdf") return "#ef4444";
  if (["txt", "md"].includes(ext)) return "#3b82f6";
  if (["jpg", "jpeg", "png"].includes(ext)) return "#8b5cf6";
  return "#10B981";
}

function extLabel(filename: string): string {
  return filename.split(".").pop()?.toUpperCase() ?? "FILE";
}

interface AIChatInputProps {
  onFileSelect?: (file: File) => void;
  isIngesting?: boolean;
  expandUp?: boolean;
  countryCode?: string;
  onResponse?: (answer: string) => void;
  provider?: string;
}

const AIChatInput = ({ onFileSelect, isIngesting = false, expandUp = false, countryCode, onResponse, provider }: AIChatInputProps) => {
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [showPlaceholder, setShowPlaceholder] = useState(true);
  const [isActive, setIsActive] = useState(false);
  const [thinkActive, setThinkActive] = useState(false);
  const [deepSearchActive, setDeepSearchActive] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [subValues, setSubValues] = useState<Record<string, string>>({ role: "", context: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<{ id: number; file: File }[]>([]);
  const [filesExpanded, setFilesExpanded] = useState(false);
  const fileIdRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    if (isLoading || isIngesting) return;

    // Files take priority — ingest each queued file, then clear the list
    if (uploadedFiles.length > 0 && onFileSelect) {
      for (const { file } of uploadedFiles) {
        await onFileSelect(file);
      }
      setUploadedFiles([]);
      setFilesExpanded(false);
      return;
    }

    if (!inputValue.trim()) return;
    setIsLoading(true);
    try {
      const res = await fetch("/api/rag/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getStoredToken()}`,
        },
        body: JSON.stringify({
          question: inputValue,
          role: subValues.role,
          context: subValues.context,
          country_code: countryCode ?? "",
          provider: provider ?? "",
        }),
      });
      const data = await res.json();
      if (data.answer) {
        onResponse?.(data.answer);
        setInputValue("");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isActive || inputValue) return;
    const interval = setInterval(() => {
      setShowPlaceholder(false);
      setTimeout(() => {
        setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDERS.length);
        setShowPlaceholder(true);
      }, 400);
    }, 3000);
    return () => clearInterval(interval);
  }, [isActive, inputValue]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        if (!inputValue) setIsActive(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [inputValue]);

  const handleActivate = () => setIsActive(true);

  const containerVariants: Variants = {
    collapsed: {
      height: 68,
      boxShadow: "0 2px 8px 0 rgba(0,0,0,0.08)",
      transition: { type: "spring", stiffness: 120, damping: 18 },
    },
    expanded: {
      height: 128,
      boxShadow: "0 8px 32px 0 rgba(0,0,0,0.16)",
      transition: { type: "spring", stiffness: 120, damping: 18 },
    },
  };

  const placeholderContainerVariants = {
    initial: {},
    animate: { transition: { staggerChildren: 0.025 } },
    exit: { transition: { staggerChildren: 0.015, staggerDirection: -1 } },
  };

  const letterVariants: Variants = {
    initial: { opacity: 0, filter: "blur(12px)", y: 10 },
    animate: {
      opacity: 1, filter: "blur(0px)", y: 0,
      transition: { opacity: { duration: 0.25 }, filter: { duration: 0.4 }, y: { type: "spring", stiffness: 80, damping: 20 } },
    },
    exit: {
      opacity: 0, filter: "blur(12px)", y: -10,
      transition: { opacity: { duration: 0.2 }, filter: { duration: 0.3 }, y: { type: "spring", stiffness: 80, damping: 20 } },
    },
  };

  const subInputItemVariants: Variants = {
    hidden: { opacity: 0, y: -8, scale: 0.98 },
    visible: (i: number) => ({
      opacity: 1, y: 0, scale: 1,
      transition: { delay: i * 0.07, type: "spring", stiffness: 200, damping: 22 },
    }),
  };

  const subRowStyle = {
    background: "#fff",
    border: "1px solid #e4eaee",
    borderRadius: 32,
    padding: "16px 20px",
    display: "flex",
    alignItems: "center",
    gap: 15,
    boxShadow: "0 2px 8px 0 rgba(0,0,0,0.06)",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.75rem",
    fontWeight: 700,
    color: "#667085",
    minWidth: 80,
    flexShrink: 0,
  };

  // Stacked card geometry
  const n = uploadedFiles.length;
  const peek = Math.min(n - 1, 2); // how many ghost cards peek behind
  const collapsedContainerH = n === 0 ? 24 : CARD_H + peek * 8;
  const expandedContainerH = n === 0 ? 24 : n * CARD_H + (n - 1) * CARD_GAP;
  const containerH = filesExpanded ? expandedContainerH : collapsedContainerH;

  return (
    <div ref={wrapperRef} className={`w-full text-black flex gap-2 ${expandUp ? "flex-col-reverse" : "flex-col"}`}>

      {/* Main chat bar */}
      <motion.div
        className="w-full"
        variants={containerVariants}
        animate={isActive || inputValue ? "expanded" : "collapsed"}
        initial="collapsed"
        style={{ overflow: "hidden", borderRadius: 32, background: "#fff", border: "1px solid #e4eaee" }}
        onClick={handleActivate}
      >
        <div className="flex flex-col items-stretch w-full h-full">
          {/* Input Row */}
          <div className="flex items-center gap-2 p-3 w-full">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.jpg,.jpeg,.png"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setUploadedFiles((prev) => [...prev, { id: fileIdRef.current++, file }]);
                e.target.value = "";
              }}
            />
            <button
              className={`p-3 rounded-full transition ${uploadedFiles.length > 0 || isIngesting ? "bg-[#10B981]/10 text-[#10B981]" : "hover:bg-gray-100"}`}
              title="Attach file"
              type="button"
              tabIndex={-1}
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip size={20} />
            </button>

            <div className="relative flex-1">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="flex-1 py-2 text-base w-full font-normal"
                style={{ position: "relative", zIndex: 1, border: "none", borderRadius: 0, boxShadow: "none", background: "transparent", padding: "8px 0", width: "100%" }}
                onFocus={handleActivate}
              />
              <div className="absolute left-0 top-0 w-full h-full pointer-events-none flex items-center px-3 py-2">
                <AnimatePresence mode="wait">
                  {showPlaceholder && !isActive && !inputValue && (
                    <motion.span
                      key={placeholderIndex}
                      className="absolute left-0 right-0 top-1/2 -translate-y-1/2 text-gray-400 select-none pointer-events-none"
                      style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", zIndex: 0 }}
                      variants={placeholderContainerVariants}
                      initial="initial"
                      animate="animate"
                      exit="exit"
                    >
                      {PLACEHOLDERS[placeholderIndex].split("").map((char, i) => (
                        <motion.span key={i} variants={letterVariants} style={{ display: "inline-block" }}>
                          {char === " " ? "\u00A0" : char}
                        </motion.span>
                      ))}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <button className="p-3 rounded-full hover:bg-gray-100 transition" title="Voice input" type="button" tabIndex={-1}>
              <Mic size={20} />
            </button>
            <button
              className="flex items-center gap-1 bg-[#10B981] hover:bg-[#059669] disabled:opacity-50 text-white p-3 rounded-full font-medium justify-center transition"
              title="Send" type="button" tabIndex={-1}
              onClick={handleSend}
              disabled={isLoading || isIngesting || (uploadedFiles.length === 0 && !inputValue.trim())}
            >
              <Send size={18} className={isLoading ? "animate-pulse" : ""} />
            </button>
          </div>

          {/* Expanded Controls */}
          <motion.div
            className="w-full flex justify-start px-4 items-center text-sm"
            variants={{
              hidden: { opacity: 0, y: 20, pointerEvents: "none" as const, transition: { duration: 0.25 } },
              visible: { opacity: 1, y: 0, pointerEvents: "auto" as const, transition: { duration: 0.35, delay: 0.08 } },
            }}
            initial="hidden"
            animate={isActive || inputValue ? "visible" : "hidden"}
            style={{ marginTop: 8 }}
          >
            <div className="flex gap-3 items-center">
              <button
                className={`flex items-center gap-1 px-4 py-2 rounded-full transition-all font-medium group ${thinkActive ? "bg-[#10B981]/10 outline outline-[#10B981]/60 text-[#065f46]" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                title="Think" type="button"
                onClick={(e) => { e.stopPropagation(); setThinkActive((a) => !a); }}
              >
                <Lightbulb className="group-hover:fill-yellow-300 transition-all" size={18} />
                Think
              </button>

              <motion.button
                className={`flex items-center px-4 gap-1 py-2 rounded-full transition font-medium whitespace-nowrap overflow-hidden justify-start ${deepSearchActive ? "bg-[#10B981]/10 outline outline-[#10B981]/60 text-[#065f46]" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                title="Deep Search" type="button"
                onClick={(e) => { e.stopPropagation(); setDeepSearchActive((a) => !a); }}
                initial={false}
                animate={{ width: deepSearchActive ? 125 : 36, paddingLeft: deepSearchActive ? 8 : 9 }}
              >
                <div className="flex-1"><Globe size={18} /></div>
                <motion.span className="pb-[2px]" initial={false} animate={{ opacity: deepSearchActive ? 1 : 0 }}>
                  Deep Search
                </motion.span>
              </motion.button>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Sub input fields — appear below the chat bar */}
      <AnimatePresence>
        {isActive && (
          <motion.div
            key="sub-inputs"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
            style={{ overflow: "hidden", display: "flex", flexDirection: "column", gap: 8 }}
          >
            {TEXT_SUB_INPUTS.map((field, i) => (
              <motion.div
                key={field.key}
                custom={i}
                variants={subInputItemVariants}
                initial="hidden"
                animate="visible"
                style={subRowStyle}
              >
                <span style={labelStyle}>{field.label}</span>
                <input
                  type="text"
                  value={subValues[field.key]}
                  onChange={(e) => setSubValues((v) => ({ ...v, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                  style={{
                    flex: 1, border: "none", boxShadow: "none", outline: "none", background: "transparent",
                    fontSize: "0.875rem", color: "#1f2933", padding: 0, borderRadius: 0, width: "100%",
                  }}
                />
              </motion.div>
            ))}

            {/* Stacked file cards — wrapper always mounted, collapses when empty */}
            <div style={{
              overflow: "hidden",
              maxHeight: n > 0 ? "600px" : 0,
              opacity: n > 0 ? 1 : 0,
              transition: "max-height 0.35s cubic-bezier(0.4,0,0.2,1), opacity 0.25s ease",
            }}>
            {(
              <motion.div
                custom={TEXT_SUB_INPUTS.length}
                variants={subInputItemVariants}
                initial="hidden"
                animate={n > 0 ? "visible" : "hidden"}
                style={{ display: "flex", flexDirection: "column", gap: 0 }}
              >
                {/* Stacked cards area */}
                <div
                  style={{ position: "relative", width: "100%", height: containerH, transition: "height 0.35s cubic-bezier(0.4,0,0.2,1)" }}
                >
                  <AnimatePresence>
                  {uploadedFiles.map(({ id, file }, i) => {
                    const color = extColor(file.name);
                    const label = extLabel(file.name);
                    const expandedY = i * (CARD_H + CARD_GAP);
                    const translateY = filesExpanded ? expandedY : i * 8;
                    const scale = filesExpanded ? 1 : Math.max(1 - i * 0.04, 0.88);
                    const opacity = filesExpanded ? 1 : i > 2 ? 0 : 1 - i * 0.15;

                    return (
                      <motion.div
                        key={id}
                        style={{ position: "absolute", left: 0, right: 0, height: CARD_H, zIndex: n - i }}
                        initial={{ x: 40, opacity: 0 }}
                        animate={{ x: 0, y: translateY, scale, opacity }}
                        exit={{ x: 60, opacity: 0, transition: { duration: 0.2, ease: "easeIn" } }}
                        transition={{ type: "spring", stiffness: 260, damping: 26, delay: filesExpanded ? i * 0.04 : (n - 1 - i) * 0.04 }}
                      >
                        <div style={{ height: "100%", background: "#fff", border: "1px solid #e4eaee", borderRadius: 9999, padding: "10px 14px", display: "flex", alignItems: "center", gap: 12, boxShadow: "0 2px 8px 0 rgba(0,0,0,0.07)" }}>
                          <div style={{ width: 36, height: 36, borderRadius: "50%", background: color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: "0.6rem", fontWeight: 800, color: "#fff" }}>{label}</div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#1f2933", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{file.name}</div>
                            <div style={{ fontSize: "0.7rem", color: "#9ca3af", marginTop: 1 }}>{(file.size / 1024).toFixed(0)} KB</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setUploadedFiles((prev) => prev.filter((entry) => entry.id !== id))}
                            style={{ flexShrink: 0, padding: 4, borderRadius: "50%", border: "none", background: "transparent", cursor: "pointer", color: "#9ca3af", display: "flex", alignItems: "center", justifyContent: "center" }}
                            className="hover:text-red-400 transition"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                  </AnimatePresence>
                </div>

                {/* Expand / collapse toggle */}
                <motion.button
                  type="button"
                  onClick={() => setFilesExpanded((v) => !v)}
                  style={{
                    marginTop: 10,
                    alignSelf: "center",
                    position: "relative",
                    padding: "8px 36px 8px 20px",
                    background: "#fff",
                    borderRadius: 9999,
                    border: "none",
                    boxShadow: "0px 3px 3.5px rgba(119,113,113,0.35)",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#1f2933",
                    cursor: "pointer",
                  }}
                  whileHover={{ y: -2, boxShadow: "0px 5px 5px rgba(119,113,113,0.4)" }}
                  whileTap={{ scale: 0.97 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  layout
                >
                  {filesExpanded ? "Collapse" : `Show all ${n} file${n !== 1 ? "s" : ""}`}
                  <motion.span
                    style={{
                      position: "absolute",
                      right: 14,
                      top: "50%",
                      marginTop: -5,
                      width: 7,
                      height: 7,
                      borderTop: "2px solid #1f2933",
                      borderLeft: "2px solid #1f2933",
                      display: "block",
                    }}
                    initial={false}
                    animate={{ rotate: filesExpanded ? 45 : 225, y: filesExpanded ? 2 : -2 }}
                    transition={{ duration: 0.3, ease: "linear" }}
                  />
                </motion.button>
              </motion.div>
            )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};

export { AIChatInput };
