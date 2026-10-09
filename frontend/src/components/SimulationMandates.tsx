"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { interpolateRgb } from "d3-interpolate";
import { scaleLinear } from "d3-scale";

type PartyData = {
  short_name: string;
  color_hex: string;
  pct: number;
  seats: number;
  is_governing: boolean;
  animatedSeats?: number;
};

type SimulationMandatesProps = {
  parties: PartyData[];
  totalSeats: number;
  threshold: number;
  animationProgress: number;
  isRunning: boolean;
};

const TOTAL_SEATS = 250;
const RADIUS = 180;
const INNER_RADIUS = 40;
const START_ANGLE = Math.PI;
const END_ANGLE = 2 * Math.PI;

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function describeArc(
  cx: number,
  cy: number,
  radius: number,
  startAngle: number,
  endAngle: number,
  innerRadius: number
) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const startInner = polarToCartesian(cx, cy, innerRadius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const endInner = polarToCartesian(cx, cy, innerRadius, startAngle);

  const largeArcFlag = endAngle - startAngle <= Math.PI ? "0" : "1";

  return [
    `M ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 1 ${startInner.x} ${startInner.y}`,
    "Z",
  ].join(" ");
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

export default function SimulationMandates({
  parties,
  totalSeats = TOTAL_SEATS,
  threshold = 3,
  animationProgress,
  isRunning,
}: SimulationMandatesProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [pulsePhase, setPulsePhase] = useState(0);

  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        setPulsePhase((p) => (p + 0.1) % (2 * Math.PI));
      }, 50);
      return () => clearInterval(interval);
    }
  }, [isRunning]);

  const sortedParties = useMemo(() => {
    const eligible = parties.filter((p) => p.pct >= threshold || p.is_governing);
    return [...eligible].sort((a, b) => b.pct - a.pct);
  }, [parties, threshold]);

  const seatAllocation = useMemo(() => {
    const seats: Record<string, number> = {};
    const eligible = sortedParties;
    if (eligible.length === 0) return seats;

    for (let i = 0; i < totalSeats; i++) {
      let bestParty = eligible[0];
      let bestQuotient = 0;
      for (const p of eligible) {
        const currentSeats = seats[p.short_name] || 0;
        const quotient = p.pct / (currentSeats + 1);
        if (quotient > bestQuotient) {
          bestQuotient = quotient;
          bestParty = p;
        }
      }
      seats[bestParty.short_name] = (seats[bestParty.short_name] || 0) + 1;
    }
    return seats;
  }, [sortedParties, totalSeats]);

  const animatedData = useMemo(() => {
    const progress = animationProgress;
    const easedProgress = easeOutCubic(progress);

    return sortedParties.map((p) => {
      const finalSeats = seatAllocation[p.short_name] || 0;
      const animatedSeats = Math.round(finalSeats * easedProgress);
      return {
        ...p,
        finalSeats,
        animatedSeats,
      };
    });
  }, [sortedParties, seatAllocation, animationProgress]);

  const centerX = 300;
  const centerY = 200;

  const arcData = useMemo(() => {
    let currentAngle = START_ANGLE;
    return animatedData.map((p) => {
      const seats = p.animatedSeats;
      if (seats === 0) return { ...p, path: "", angle: 0, midAngle: 0 };

      const seatAngle = (END_ANGLE - START_ANGLE) * (seats / totalSeats);
      const angle = seatAngle;
      const path = describeArc(centerX, centerY, RADIUS, currentAngle, currentAngle + angle, INNER_RADIUS);
      const midAngle = currentAngle + angle / 2;

      currentAngle += angle;
      return { ...p, path, angle, midAngle };
    });
  }, [animatedData]);

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex items-center justify-between mb-4 px-2">
        <h3 className="text-sm font-semibold text-white">Simulacija raspodele mandata</h3>
        <div className="flex items-center gap-3 text-xs text-white/60">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Vladajuće</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500/50" />
            <span>Opozicija</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500/30" />
            <span>Prag {threshold}%</span>
          </span>
        </div>
      </div>

      <div className="flex-1 relative flex items-center justify-center">
        <svg
          viewBox="0 0 600 400"
          className="w-full h-full max-w-md"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <style>{`
              @keyframes seat-pulse {
                0%, 100% { opacity: 0.6; }
                50% { opacity: 1; }
              }
              @keyframes count-up {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
              }
            `}</style>
          </defs>

          <circle
            cx={centerX}
            cy={centerY}
            r={INNER_RADIUS - 5}
            fill="#0b0d12"
            stroke="white/10"
            strokeWidth={1}
          />

          <g filter="url(#glow)">
            {arcData.map((p, i) => {
              if (!p.path) return null;
              const isGoverning = p.is_governing;
              const isHovered = false;
              const delay = i * 80;

              return (
                <g key={p.short_name}>
                  <path
                    d={p.path}
                    fill={p.color_hex}
                    fillOpacity={0.95}
                    stroke="white"
                    strokeWidth={1}
                    strokeOpacity={0.3}
                    style={{
                      filter: isRunning ? "url(#glow)" : "none",
                      transition: "fill-opacity 200ms, stroke-width 150ms",
                    }}
                    onMouseEnter={() => {}}
                    onMouseLeave={() => {}}
                  />
                  {p.animatedSeats > 0 && (
                    <text
                      x={centerX}
                      y={centerY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize="11"
                      fontWeight="700"
                      fontFamily="monospace"
                      style={{
                        pointerEvents: "none",
                        textShadow: "0 0 4px #000",
                        animation: `count-up 0.6s ease-out ${i * 60}ms forwards`,
                        opacity: 0,
                      }}
                      transform={`rotate(${180 / Math.PI * p.midAngle} ${centerX} ${centerY}) translate(0, -${RADIUS / 2 + INNER_RADIUS / 2}) rotate(${180 / Math.PI * -p.midAngle})`}
                    >
                      {p.animatedSeats}
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          <circle
            cx={centerX}
            cy={centerY}
            r={INNER_RADIUS - 5}
            fill="none"
            stroke="white/10"
            strokeWidth={1}
            strokeDasharray="4 4"
          />

          <text
            x={centerX}
            y={centerY - 5}
            textAnchor="middle"
            fill="white/40"
            fontSize="10"
            fontWeight="500"
          >
            UKUPNO
          </text>
          <text
            x={centerX}
            y={centerY + 12}
            textAnchor="middle"
            fill="white"
            fontSize="28"
            fontWeight="700"
            fontFamily="monospace"
          >
            {animatedData.reduce((s, p) => s + p.animatedSeats, 0)} / {totalSeats}
          </text>
        </svg>
      </div>

      <div className="mt-4 space-y-2 max-h-64 overflow-y-auto pr-2">
        {animatedData.map((p, i) => {
          const isGoverning = p.is_governing;
          return (
            <div
              key={p.short_name}
              className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors group"
              style={{
                animation: `count-up 0.4s ease-out ${i * 40}ms forwards`,
                opacity: 0,
              }}
            >
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ background: p.color_hex }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">
                  {p.short_name}
                  {p.is_governing && (
                    <span className="ml-1.5 px-1 py-0.5 text-[9px] rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      Vlada
                    </span>
                  )}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <div
                    className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden"
                  >
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out"
                      style={{
                        width: `${(p.animatedSeats / totalSeats) * 100}%`,
                        background: p.color_hex,
                      }}
                    />
                  </div>
                  <span className="text-[10px] text-white/50 tabular-nums w-12 text-right">
                    {p.animatedSeats}
                  </span>
                  <span className="text-[10px] text-white/30 tabular-nums w-10 text-right">
                    {p.pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          );
        })}
        <div className="pt-2 border-t border-white/10 flex items-center justify-between text-xs">
          <span className="text-white/50">
            Ukupno dodeljeno: <span className="text-white font-mono">
              {animatedData.reduce((s, p) => s + p.animatedSeats, 0)}
            </span> / {totalSeats}
          </span>
          <span className="text-white/40">
            Prag: {threshold}%
          </span>
        </div>
      </div>
    </div>
  );
}