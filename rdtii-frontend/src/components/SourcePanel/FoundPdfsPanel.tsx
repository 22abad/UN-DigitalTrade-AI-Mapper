import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { FileText } from "lucide-react";

const CARD_H = 52;
const CARD_GAP = 8;

function pdfName(url: string): string {
  try {
    const path = new URL(url).pathname;
    return decodeURIComponent(path.split("/").pop() || url);
  } catch {
    return url;
  }
}

interface Props {
  urls: string[];
  onSelect?: (url: string) => void;
  loading?: boolean;
}

export function FoundPdfsPanel({ urls, onSelect, loading = false }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (urls.length === 0) return null;

  const n = urls.length;
  const peek = Math.min(n - 1, 2);
  const collapsedH = CARD_H + peek * 8;
  const expandedH = n * CARD_H + (n - 1) * CARD_GAP;
  const containerH = expanded ? expandedH : collapsedH;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="w-full flex flex-col gap-2"
    >
      <p className="text-xs text-gray-400 px-1">
        {n} PDF{n !== 1 ? "s" : ""} found on this page
      </p>

      {/* Stacked cards */}
      <div style={{ position: "relative", height: containerH, transition: "height 0.35s cubic-bezier(0.4,0,0.2,1)" }}>
        <AnimatePresence>
          {urls.map((url, i) => {
            const translateY = expanded ? i * (CARD_H + CARD_GAP) : i * 8;
            const scale = expanded ? 1 : Math.max(1 - i * 0.04, 0.88);
            const opacity = expanded ? 1 : i > 2 ? 0 : 1 - i * 0.15;

            return (
              <motion.div
                key={url}
                style={{ position: "absolute", left: 0, right: 0, height: CARD_H, zIndex: n - i }}
                animate={{ y: translateY, scale, opacity }}
                transition={{ type: "spring", stiffness: 260, damping: 26, delay: expanded ? i * 0.04 : (n - 1 - i) * 0.04 }}
              >
                <div
                  style={{
                    height: "100%",
                    background: "#fff",
                    border: "1px solid #e4eaee",
                    borderRadius: 9999,
                    padding: "10px 14px",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                  }}
                >
                  <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#fee2e2", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <FileText size={14} color="#ef4444" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#1f2933", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {pdfName(url)}
                    </div>
                    <div style={{ fontSize: "0.68rem", color: "#9ca3af", marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {url}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onSelect?.(url)}
                    disabled={loading}
                    style={{ flexShrink: 0, padding: "3px 10px", borderRadius: 9999, border: "1px solid #10B981", background: "transparent", color: "#10B981", fontSize: "0.68rem", fontWeight: 600, cursor: loading ? "wait" : "pointer", opacity: loading ? 0.6 : 1 }}
                    className="hover:bg-[#10B981] hover:text-white transition"
                  >
                    {loading ? "Loading…" : "Select"}
                  </button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Expand / collapse toggle */}
      {n > 1 && (
        <motion.button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          style={{
            alignSelf: "center",
            position: "relative",
            padding: "6px 32px 6px 16px",
            background: "#fff",
            borderRadius: 9999,
            border: "none",
            boxShadow: "0px 3px 3.5px rgba(119,113,113,0.25)",
            fontSize: "0.72rem",
            fontWeight: 600,
            color: "#1f2933",
            cursor: "pointer",
          }}
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.97 }}
        >
          {expanded ? "Collapse" : `Show all ${n} PDFs`}
          <motion.span
            style={{ position: "absolute", right: 12, top: "50%", marginTop: -4, width: 6, height: 6, borderTop: "2px solid #1f2933", borderLeft: "2px solid #1f2933", display: "block" }}
            animate={{ rotate: expanded ? 45 : 225, y: expanded ? 2 : -2 }}
            transition={{ duration: 0.25 }}
          />
        </motion.button>
      )}
    </motion.div>
  );
}
