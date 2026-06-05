import { useRef } from "react";
import { useInView } from "motion/react";
import { WorldMap } from "./WorldMap";

const TRADE_ROUTES = [
  { start: { lat: 35.6762, lng: 139.6503 }, end: { lat: 1.3521, lng: 103.8198 } },
  { start: { lat: 1.3521, lng: 103.8198 }, end: { lat: 48.8566, lng: 2.3522 } },
  { start: { lat: 31.2304, lng: 121.4737 }, end: { lat: 51.5074, lng: -0.1278 } },
  { start: { lat: 37.7749, lng: -122.4194 }, end: { lat: 35.6762, lng: 139.6503 } },
  { start: { lat: -33.8688, lng: 151.2093 }, end: { lat: 22.3193, lng: 114.1694 } },
];

export function Placeholder() {
  const ref = useRef(null);
  useInView(ref, { once: true, margin: "0px 0px -80px 0px" });

  return (
    <section ref={ref} className="relative bg-white overflow-hidden border-t border-[#10B981]/40">

      {/* World map */}
      <div className="relative w-full h-[860px]">
        <WorldMap dots={TRADE_ROUTES} lineColor="#065f46" />
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent" />
      </div>

      {/* Content below the map */}
      <div className="relative z-10 max-w-5xl mx-auto flex flex-col items-center gap-4 px-6 pb-16 -mt-10">
        <h1 className="text-2xl md:text-4xl font-semibold mb-6">
            Search laws from Map
        </h1>
        <p className="text-[#065f46]/60 text-center max-w-md text-sm -mt-5">Automated RDTII grading system for UN ESCAP researchers to map legal evidence across all 12 pillars.</p>
        <a
          href="/mapsearch"
          className="group mt-2 px-8 py-3 rounded-full bg-[#10B981] text-white font-medium hover:bg-[#10B981]/80 transition inline-flex items-center"
        >
          <span>Global Search</span>
          <span className="overflow-hidden w-0 group-hover:w-4 transition-all duration-300 inline-flex items-center justify-center align-middle">
            <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </span>
        </a>
      </div>

    </section>
  );
}
