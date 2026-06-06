import { useRef, useMemo } from "react";
import { motion } from "motion/react";
import DottedMap from "dotted-map";

interface Dot {
  start: { lat: number; lng: number; label?: string };
  end: { lat: number; lng: number; label?: string };
}

interface WorldMapProps {
  dots?: Dot[];
  lineColor?: string;
  animationDuration?: number;
  loop?: boolean;
}

export function WorldMap({
  dots = [],
  lineColor = "#10B981",
  animationDuration = 2,
  loop = true,
}: WorldMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const map = useMemo(() => new DottedMap({ height: 100, grid: "diagonal" }), []);

  const svgMap = useMemo(
    () =>
      map.getSVG({
        radius: 0.22,
        color: "rgb(30, 137, 98)",
        shape: "circle",
        backgroundColor: "transparent",
      }),
    [map],
  );

  const projectPoint = (lat: number, lng: number) => ({
    x: (lng + 180) * (800 / 360),
    y: (90 - lat) * (400 / 180),
  });

  const createCurvedPath = (
    start: { x: number; y: number },
    end: { x: number; y: number },
  ) => {
    const midX = (start.x + end.x) / 2;
    const midY = Math.min(start.y, end.y) - 50;
    return `M ${start.x} ${start.y} Q ${midX} ${midY} ${end.x} ${end.y}`;
  };

  const staggerDelay = 0.3;
  const totalAnimationTime = dots.length * staggerDelay + animationDuration;
  const fullCycleDuration = totalAnimationTime + 2;

  return (
    <div className="w-full h-full relative overflow-hidden">
      <img
        src={`data:image/svg+xml;utf8,${encodeURIComponent(svgMap)}`}
        className="absolute inset-0 w-full h-full object-cover opacity-100 pointer-events-none select-none"
        style={{ maskImage: "linear-gradient(to bottom, transparent, white 0%, white 20%, transparent)" }}
        alt=""
        draggable={false}
      />

      <svg
        ref={svgRef}
        viewBox="0 0 800 400"
        className="absolute inset-0 w-full h-full pointer-events-none select-none"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="wm-path-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="white" stopOpacity="0" />
            <stop offset="5%" stopColor={lineColor} stopOpacity="1" />
            <stop offset="60%" stopColor={lineColor} stopOpacity="1" />
            <stop offset="80%" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <filter id="wm-glow">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {dots.map((dot, i) => {
          const s = projectPoint(dot.start.lat, dot.start.lng);
          const e = projectPoint(dot.end.lat, dot.end.lng);
          const path = createCurvedPath(s, e);
          const startTime = (i * staggerDelay) / fullCycleDuration;
          const endTime = (i * staggerDelay + animationDuration) / fullCycleDuration;
          const resetTime = totalAnimationTime / fullCycleDuration;

          return (
            <g key={i}>
              <motion.path
                d={path}
                fill="none"
                stroke="url(#wm-path-gradient)"
                strokeWidth="1"
                initial={{ pathLength: 0 }}
                animate={loop ? { pathLength: [0, 0, 1, 1, 0] } : { pathLength: 1 }}
                transition={
                  loop
                    ? { duration: fullCycleDuration, times: [0, startTime, endTime, resetTime, 1], ease: "easeInOut", repeat: Infinity }
                    : { duration: animationDuration, delay: i * staggerDelay, ease: "easeInOut" }
                }
              />
              {loop && (
                <motion.circle
                  r="3"
                  fill={lineColor}
                  filter="url(#wm-glow)"
                  initial={{ offsetDistance: "0%", opacity: 0 }}
                  animate={{ offsetDistance: [null, "0%", "100%", "100%", "100%"], opacity: [0, 0, 1, 0, 0] }}
                  transition={{ duration: fullCycleDuration, times: [0, startTime, endTime, resetTime, 1], ease: "easeInOut", repeat: Infinity }}
                  style={{ offsetPath: `path('${path}')` } as React.CSSProperties}
                />
              )}

              {/* Pulsing dots */}
              {[s, e].map((pt, j) => (
                <g key={j}>
                  <circle cx={pt.x} cy={pt.y} r="3" fill={lineColor} filter="url(#wm-glow)" />
                  <circle cx={pt.x} cy={pt.y} r="3" fill={lineColor} opacity="0.4">
                    <animate attributeName="r" from="3" to="10" dur="2s" begin={`${j * 0.5}s`} repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.5" to="0" dur="2s" begin={`${j * 0.5}s`} repeatCount="indefinite" />
                  </circle>
                </g>
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
