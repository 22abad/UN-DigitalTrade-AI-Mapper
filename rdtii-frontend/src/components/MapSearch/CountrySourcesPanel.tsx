import { motion, AnimatePresence } from "motion/react";
import { X, ExternalLink } from "lucide-react";
import { getLegalSources } from "../../data/legalSources";

interface Props {
  countryCode: string | null;
  countryName: string;
  onClose: () => void;
}

const FLAG_BASE = "https://flagcdn.com/24x18";

export function CountrySourcesPanel({ countryCode, countryName, onClose }: Props) {
  const sources = countryCode ? getLegalSources(countryCode) : [];

  return (
    <AnimatePresence>
      {countryCode && (
        <motion.div
          key="sources-panel"
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          transition={{ type: "spring", stiffness: 280, damping: 28 }}
          className="fixed left-4 top-1/2 z-50 w-72"
          style={{ transform: "translateY(-50%)" }}
        >
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: "rgba(255,255,255,0.92)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(0,0,0,0.08)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-black/5">
              <div className="flex items-center gap-2">
                <img
                  src={`${FLAG_BASE}/${countryCode.toLowerCase()}.png`}
                  alt={countryName}
                  className="rounded-sm"
                  style={{ width: 24, height: 18 }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
                <span className="font-semibold text-sm text-gray-800">{countryName}</span>
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 bg-gray-200/10 hover:text-gray-600 transition p-1 rounded-full hover:bg-gray-100"
              >
                <X size={14} />
              </button>
            </div>

            {/* Sources list */}
            <div className="px-3 py-2 flex flex-col gap-1">
              <p className="text-xs text-gray-400 px-1 pb-1">Top legal & legislation sources</p>
              {sources.length === 0 ? (
                <p className="text-xs text-gray-400 px-1 py-2">No sources available yet.</p>
              ) : (
                sources.map((source, i) => (
                  <a
                    key={i}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-2 px-2 py-2 rounded-xl hover:bg-[#10B981]/8 transition group"
                  >
                    <div className="flex-shrink-0 w-5 h-5 rounded-full bg-[#10B981]/10 flex items-center justify-center mt-0.5">
                      <span className="text-[10px] font-bold text-[#10B981]">{i + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className="text-xs font-medium text-gray-800 truncate">{source.name}</span>
                        <ExternalLink size={10} className="flex-shrink-0 text-gray-300 group-hover:text-[#10B981] transition" />
                      </div>
                      <span className="text-[11px] text-gray-400 leading-tight">{source.description}</span>
                    </div>
                  </a>
                ))
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
