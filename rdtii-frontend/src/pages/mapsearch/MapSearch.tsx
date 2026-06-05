import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import WorldMap from "react-svg-worldmap";
import { SideBar } from "../../components/SideBar";
import { AIChatInput } from "../../components/Workbench/ChatInput";
import { CountrySourcesPanel } from "../../components/MapSearch/CountrySourcesPanel";
import ColorBends from "../../components/ColorBends/ColorBends";
import { AnimatePresence, motion } from "motion/react";
import { Plus, Menu, X, Home, AppWindowMac, User } from "lucide-react";
import { GooeyFilter } from "../../components/ui/gooey-filter";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ESCAP_DATA: any[] = [
  { country: "cn", value: 1 },
  { country: "in", value: 1 },
  { country: "sg", value: 1 },
  { country: "th", value: 1 },
  { country: "au", value: 1 },
  { country: "ph", value: 1 },
  { country: "jp", value: 1 },
  { country: "kr", value: 1 },
  { country: "id", value: 1 },
  { country: "my", value: 1 },
  { country: "vn", value: 1 },
  { country: "bd", value: 1 },
  { country: "pk", value: 1 },
  { country: "lk", value: 1 },
  { country: "np", value: 1 },
  { country: "kz", value: 1 },
  { country: "uz", value: 1 },
  { country: "mn", value: 1 },
  { country: "nz", value: 1 },
  { country: "fj", value: 1 },
];

const MIN_SCALE = 2.5;
const MAX_SCALE = 10;
const INITIAL_SCALE = 4;
const INITIAL_X = 0;
const INITIAL_Y = 0;

function clampOffset(x: number, y: number, scale: number) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const mapW = Math.min(vh, vw) * 0.75 * scale;
  const mapH = mapW * 0.75;
  const margin = 0.2;
  return {
    x: Math.max(-mapW / 2 + vw * margin, Math.min(mapW / 2 - vw * margin, x)),
    y: Math.max(-mapH / 2 + vh * margin, Math.min(mapH / 2 - vh * margin, y)),
  };
}

export function MapSearchPage() {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dragEnabled, setDragEnabled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [ragAnswer, setRagAnswer] = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<{ code: string; name: string } | null>(null);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  // State for rendering; refs mirror state so event handlers always read fresh values
  const [scale, _setScale] = useState(INITIAL_SCALE);
  const [offset, _setOffset] = useState({ x: INITIAL_X, y: INITIAL_Y });
  const scaleRef  = useRef(INITIAL_SCALE);
  const offsetRef = useRef({ x: INITIAL_X, y: INITIAL_Y });

  const [mapSize, setMapSize] = useState(() =>
    Math.min(window.innerHeight, window.innerWidth) * 0.75,
  );
  const containerRef = useRef<HTMLDivElement>(null);

  const applyTransform = useCallback((s: number, o: { x: number; y: number }) => {
    scaleRef.current  = s;
    offsetRef.current = o;
    _setScale(s);
    _setOffset(o);
  }, []);

  useEffect(() => {
    const onResize = () =>
      setMapSize(Math.min(window.innerHeight, window.innerWidth) * 0.75);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // ── Photo-zoom: pointer events + absolute snapshot (no delta accumulation) ──

  // Active pointers tracked by ID
  const pointersRef = useRef(new Map<number, { x: number; y: number }>());

  // Snapshot captured when 2nd finger lands
  const gestureSnapRef = useRef<{
    scale:  number;
    offset: { x: number; y: number };
    mid:    { x: number; y: number };
    dist:   number;
  } | null>(null);

  // Snapshot captured when drag starts
  const panSnapRef = useRef<{
    offset: { x: number; y: number };
    x: number;
    y: number;
  } | null>(null);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === "mouse") {
      if (e.button === 1) {
        // Middle mouse (wheel press) — always drags, matches classic map UX
        e.preventDefault();
      } else if (e.button === 0 && dragEnabled) {
        // Left click — only drags when drag-mode toggle is active
      } else {
        return;
      }
    }
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    const pts = [...pointersRef.current.values()];
    if (pts.length >= 2) {
      const [p0, p1] = pts;
      gestureSnapRef.current = {
        scale:  scaleRef.current,
        offset: { ...offsetRef.current },
        mid:    { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 },
        dist:   Math.hypot(p0.x - p1.x, p0.y - p1.y),
      };
      panSnapRef.current = null;
    } else {
      panSnapRef.current = { offset: { ...offsetRef.current }, x: e.clientX, y: e.clientY };
      gestureSnapRef.current = null;
    }
  }, [dragEnabled]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!pointersRef.current.has(e.pointerId)) return;
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });

    const pts = [...pointersRef.current.values()];
    const vw  = window.innerWidth;
    const vh  = window.innerHeight;

    if (pts.length >= 2 && gestureSnapRef.current) {
      const snap = gestureSnapRef.current;
      const [p0, p1] = pts;
      const currDist = Math.hypot(p0.x - p1.x, p0.y - p1.y);
      const currMid  = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };

      // Absolute: every frame is computed from the gesture snapshot, never from prev frame
      const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, snap.scale * (currDist / snap.dist)));
      const ratio    = newScale / snap.scale;
      applyTransform(newScale, clampOffset(
        currMid.x - vw / 2 - ratio * (snap.mid.x - vw / 2 - snap.offset.x),
        currMid.y - vh / 2 - ratio * (snap.mid.y - vh / 2 - snap.offset.y),
        newScale,
      ));
    } else if (pts.length === 1 && panSnapRef.current) {
      const snap = panSnapRef.current;
      applyTransform(scaleRef.current, clampOffset(
        snap.offset.x + e.clientX - snap.x,
        snap.offset.y + e.clientY - snap.y,
        scaleRef.current,
      ));
    }
  }, [applyTransform]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    pointersRef.current.delete(e.pointerId);
    const pts = [...pointersRef.current.values()];

    if (pts.length === 1) {
      // One finger lifted mid-pinch — seamlessly resume pan from remaining finger
      panSnapRef.current    = { offset: { ...offsetRef.current }, x: pts[0].x, y: pts[0].y };
      gestureSnapRef.current = null;
    } else if (pts.length === 0) {
      panSnapRef.current    = null;
      gestureSnapRef.current = null;
    }
  }, []);

  const onWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    // Normalize deltaMode: lines (1) → px equivalent; pages (2) → px equivalent
    const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 400 : e.deltaY;
    // Exponential factor — proportional to scroll magnitude so trackpad micro-oscillations
    // produce near-zero zoom instead of a full ±10% jump (which causes visible shaking)
    const factor   = Math.exp(-px / 500);
    const vw       = window.innerWidth;
    const vh       = window.innerHeight;
    const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scaleRef.current * factor));
    const ratio    = newScale / scaleRef.current;
    applyTransform(newScale, clampOffset(
      e.clientX - vw / 2 - (e.clientX - vw / 2 - offsetRef.current.x) * ratio,
      e.clientY - vh / 2 - (e.clientY - vh / 2 - offsetRef.current.y) * ratio,
      newScale,
    ));
  }, [applyTransform]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [onWheel]);

  useEffect(() => {
    const style = document.createElement("style");
    style.id = "map-hover-style";
    style.textContent = `
      #world-map path { transition: fill-opacity 0.12s; outline: none; }
      #world-map path:hover { fill-opacity: 1 !important; stroke-opacity: 1 !important; }
      #world-map *:focus { outline: none; }
    `;
    document.head.appendChild(style);
    return () => { const el = document.getElementById("map-hover-style"); if (el) el.remove(); };
  }, []);

  return (
    <div className="flex overflow-hidden" style={{ height: "100dvh" }}>

      {/* Full-page background */}
      <div className="fixed inset-0 -z-10" style={{ height: "100dvh" }}>
        <ColorBends colors={["#0d3326", "#072418"]} speed={0.15} intensity={1.2} noise={0.1} frequency={0.8} />
      </div>
      <div className="fixed inset-0 -z-10 bg-white/65" style={{ height: "100dvh" }} />
      <div
        className="fixed inset-0 -z-10 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0, 80, 63, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 80, 63, 0.05) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* World map with scroll zoom */}
        <div
          ref={containerRef}
          id="world-map"
          className="fixed inset-0 overflow-hidden"
        style={{ zIndex: 1, display: "flex", alignItems: "center", justifyContent: "center", cursor: dragEnabled ? "grab" : "default", touchAction: "none" }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            transformOrigin: "center center",
            pointerEvents: dragEnabled ? "none" : undefined,
          }}
          onMouseOver={(e) => {
            const code = (e.target as Element).closest("path")?.querySelector("title")?.textContent;
            if (code) setHoveredCountry(code);
          }}
          onMouseLeave={() => setHoveredCountry(null)}
        >
          <style>{`
            .worldmap__figure-container path { cursor: pointer; paint-order: stroke fill; }
          `}</style>
          <WorldMap
            color="#10B981"
            backgroundColor="transparent"
            borderColor="#10B981"
            size={mapSize}
            data={ESCAP_DATA}
            tooltipTextFunction={({ countryCode }) => countryCode.toUpperCase()}
            styleFunction={({ countryCode }) => {
              const code = countryCode.toUpperCase();
              const isSelected = selectedCountry?.code === code;
              const isHovered  = hoveredCountry === code;
              return {
                fill: "#10B981",
                fillOpacity: isSelected ? 1 : isHovered ? 0.65 : 0.25,
                stroke: "#10B981",
                strokeOpacity: 1,
                strokeWidth: isSelected ? 1.2 : isHovered ? 0.8 : 0.3,
              };
            }}
            onClickFunction={({ countryCode, countryName }) => {
              const code = countryCode.toUpperCase();
              setSelectedCountry((prev) =>
                prev?.code === code ? null : { code, name: countryName }
              );
            }}
          />
        </div>
      </div>

      {/* Sidebar */}
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
                variant="mapsearch"
                country=""
                provider=""
                status="idle"
                mappingsCount={0}
                pendingCount={0}
                sourceUrl=""
                availableProviders={[]}
                selectedProvider=""
                setSelectedProvider={() => {}}
                onClose={() => setSidebarOpen(false)}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Sidebar toggle */}
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

      {/* Gooey Filter Menu */}
      <GooeyFilter id="gooey-filter-menu" strength={5} />
      <div
        className="fixed top-4 right-4 z-50"
        style={{ filter: "url(#gooey-filter-menu)" }}
      >
        <AnimatePresence>
          {menuOpen && [
            { icon: Home, key: "home", onClick: () => { setMenuOpen(false); navigate("/"); } },
            { icon: AppWindowMac, key: "workbench", onClick: () => { setMenuOpen(false); navigate("/workbench"); } },
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

      {/* Bottom AI chat bar — overlays the map, centered, pointer-events contained */}
      <div className="fixed bottom-6 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
        <div className="w-full max-w-2xl pointer-events-auto flex flex-col gap-3">
          <AnimatePresence>
            {ragAnswer && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.25 }}
                className="relative w-full rounded-2xl p-4 text-sm"
                style={{ background: "rgba(255,255,255,0.92)", backdropFilter: "blur(12px)", border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 4px 24px rgba(0,0,0,0.1)", color: "#1a2e26" }}
              >
                <button
                  className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition"
                  onClick={() => setRagAnswer(null)}
                >
                  <X size={14} />
                </button>
                <p className="leading-relaxed pr-4 whitespace-pre-wrap">{ragAnswer}</p>
              </motion.div>
            )}
          </AnimatePresence>
          <AIChatInput expandUp onResponse={setRagAnswer} />
        </div>
      </div>

      {/* Country sources panel */}
      <CountrySourcesPanel
        countryCode={selectedCountry?.code ?? null}
        countryName={selectedCountry?.name ?? ""}
        onClose={() => setSelectedCountry(null)}
      />

    </div>
  );
}
