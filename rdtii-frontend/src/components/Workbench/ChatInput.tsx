import { useState, useEffect, useRef } from "react";
import { Lightbulb, Mic, Globe, Paperclip, Send } from "lucide-react";
import { AnimatePresence, motion, type Variants } from "motion/react";

const PLACEHOLDERS = [
  "Summarise the cross-border data flow obligations...",
  "Which clauses relate to Pillar 6 indicators?",
  "Extract consent requirements from this text...",
  "Compare this law against RDTII 2.1 standards...",
  "Find data localisation provisions in the source...",
  "Identify breach notification requirements...",
];

const SUB_INPUTS = [
  { key: "role", label: "Role", placeholder: "e.g. Legal analyst, Policy researcher..." },
  { key: "context", label: "Context", placeholder: "e.g. Reviewing Singapore's PDPA amendments..." },
  { key: "format", label: "Output format", placeholder: "e.g. Bullet points, structured JSON, summary..." },
];

const AIChatInput = () => {
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [showPlaceholder, setShowPlaceholder] = useState(true);
  const [isActive, setIsActive] = useState(false);
  const [thinkActive, setThinkActive] = useState(false);
  const [deepSearchActive, setDeepSearchActive] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [subValues, setSubValues] = useState<Record<string, string>>({ role: "", context: "", format: "" });
  const wrapperRef = useRef<HTMLDivElement>(null);

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

  const subInputVariants: Variants = {
    hidden: { opacity: 0, y: -8, scale: 0.98 },
    visible: (i: number) => ({
      opacity: 1, y: 0, scale: 1,
      transition: { delay: i * 0.07, type: "spring", stiffness: 200, damping: 22 },
    }),
    exit: (i: number) => ({
      opacity: 0, y: -6, scale: 0.97,
      transition: { delay: i * 0.03, duration: 0.15 },
    }),
  };

  return (
    <div ref={wrapperRef} className="w-full text-black flex flex-col gap-2">

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
            <button className="p-3 rounded-full hover:bg-gray-100 transition" title="Attach file" type="button" tabIndex={-1}>
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
                      className="absolute left-0 top-1/2 -translate-y-1/2 text-gray-400 select-none pointer-events-none"
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
            <button className="flex items-center gap-1 bg-[#10B981] hover:bg-[#059669] text-white p-3 rounded-full font-medium justify-center" title="Send" type="button" tabIndex={-1}>
              <Send size={18} />
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
        {isActive && SUB_INPUTS.map((field, i) => (
          <motion.div
            key={field.key}
            custom={i}
            variants={subInputVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{
              background: "#fff",
              border: "1px solid #e4eaee",
              borderRadius: 32,
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              gap: 15,
              boxShadow: "0 2px 8px 0 rgba(0,0,0,0.06)",
            }}
          >
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#667085", minWidth: 80 }}>
              {field.label}
            </span>
            <input
              type="text"
              value={subValues[field.key]}
              onChange={(e) => setSubValues((v) => ({ ...v, [field.key]: e.target.value }))}
              placeholder={field.placeholder}
              style={{
                flex: 1, border: "none", boxShadow: "none", outline: "none", background: "transparent",
                fontSize: "0.875rem", color: "#1f2933", padding: 0, borderRadius: 0,
                width: "100%",
              }}
            />
          </motion.div>
        ))}
      </AnimatePresence>

    </div>
  );
};

export { AIChatInput };
