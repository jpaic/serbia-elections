"use client";

import { useMemo } from "react";
import type { PartyData } from "@/lib/types";

const TOTAL_SEATS = 250;
const RADIUS = 180;
const INNER_RADIUS = 40;
const START_ANGLE = Math.PI;
const END_ANGLE = 2 * Math.PI;

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
}

function describeArc(
  cx: number, cy: number, radius: number,
  startAngle: number, endAngle: number, innerRadius: number
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

function easeOutCubic(t: number) { return 1 - Math.pow(1 - t, 3); }

interface SimulationMandatesProps {
  parties: PartyData[];
  totalSeats?: number;
  threshold?: number;
  animationProgress: number;
  isRunning: boolean;
}

export default function SimulationMandates({
  parties,
  totalSeats = TOTAL_SEATS,
  threshold = 3,
  animationProgress,
  isRunning,
}: SimulationMandatesProps) {
  // Sort by ballot_number (RIK order)
  const sortedParties = useMemo(() => {
    return [...parties].sort((a, b) => (a.ballot_number ?? 999) - (b.ballot_number ?? 999));
  }, [parties]);

  const easedProgress = useMemo(() => 1 - Math.pow(1 - animationProgress, 3), [animationProgress]);
  const showMandates = animationProgress >= 1.0;

  // Animated data: interpolate pct, votes. Seats only at 100% from backend.
  const animatedData = useMemo(() => {
    return sortedParties.map((p) => {
      const finalSeats = p.seats_mean ?? 0; // Use backend seats
      const finalVotes = p.votes_mean ?? Math.round(p.pct / 100 * 3_800_000); // fallback
      
      return {
        ...p,
        finalSeats,
        finalVotes,
        animatedPct: p.pct * animationProgress, // Linear progress for percentages
        animatedVotes: Math.round((p.votes_mean ?? 0) * animationProgress),
        animatedSeats: animationProgress >= 1.0 ? (p.seats_mean ?? 0) : 0, // Seats only at 100%
        showMandates: animationProgress >= 1.0,
        // Backend seat data for 100% view
        seatsMean: p.seats_mean,
        seatsCiLower: p.seats_ci_lower,
        seatsCiUpper: p.seats_ci_upper,
        seatsDistribution: p.seats_distribution,
        thresholdClearedProb: p.threshold_cleared_prob,
      };
    });
  }, [sortedParties, animationProgress]);

  // Arc data for semicircle (use backend seats at 100%, empty during animation)
  const centerX = 300, centerY = 200;
  const arcData = useMemo(() => {
    if (!showMandates) return [];
    let angle = START_ANGLE;
    return sortedParties.map((p) => {
      const seats = p.seats_mean ?? 0;
      if (seats === 0) return { ...p, path: "", midAngle: 0 };
      const seatAngle = (END_ANGLE - START_ANGLE) * (seats / totalSeats);
      const path = describeArc(centerX, centerY, RADIUS, angle, angle + seatAngle, INNER_RADIUS);
      const mid = angle + seatAngle / 2;
      angle += seatAngle;
      return { ...p, path, midAngle: mid };
    });
  }, [sortedParties]);

  // Total seats at 100%
  const totalSeatsAtEnd = showMandates 
    ? Math.round(sortedParties.reduce((s, p) => s + (p.seats_mean ?? 0), 0))
    : 0;

  return (
    <div className="flex flex-col h-full w-full min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 px-2">
        <h3 className="text-sm font-semibold text-white">Simulacija raspodele mandata</h3>
        <div className="flex items-center gap-3 text-xs text-white/60">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /><span>manjinska</span></span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500/50" /><span>vlada</span></span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500/30" /><span>prag {threshold}%</span></span>
        </div>
      </div>

      {/* Semicircle + Center */}
      <div className="flex-1 relative flex items-center justify-center min-h-0">
        <svg viewBox="0 0 600 400" className="w-full h-full max-w-md" preserveAspectRatio="xMidYMid meet">
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <style>{`
              @keyframes count-up { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
              @keyframes bar-grow { from { width: 0; } to { width: var(--w); } }
            `}</style>
          </defs>

          <circle cx={centerX} cy={centerY} r={INNER_RADIUS - 5} fill="#0b0d12" stroke="white/10" strokeWidth={1} />

          {/* Semicircle arcs - only at 100% */}
          <g filter="url(#glow)">
            {arcData.map((p, i) => {
              if (!p.path || (p.seats_mean ?? 0) === 0) return null;
              return (
                <g key={p.short_name}>
                  <path d={p.path} fill={p.color_hex} fillOpacity={0.95} stroke="white" strokeWidth={1} strokeOpacity={0.3} />
                  <text
                    x={centerX} y={centerY} textAnchor="middle" dominantBaseline="middle"
                    fill="white" fontSize="11" fontWeight="700" fontFamily="monospace"
                    style={{ pointerEvents: "none", textShadow: "0 0 4px #000", animation: `count-up 0.4s ease-out ${i * 40}ms forwards`, opacity: 0 }}
                    transform={`rotate(${180 / Math.PI * p.midAngle} ${centerX} ${centerY}) translate(0, -${RADIUS / 2 + INNER_RADIUS / 2}) rotate(${180 / Math.PI * -p.midAngle})`}>
                    {Math.round(p.seats_mean ?? 0)}
                  </text>
                </g>
              );
            })}
          </g>

          <circle cx={centerX} cy={centerY} r={INNER_RADIUS - 5} fill="none" stroke="white/10" strokeWidth={1} strokeDasharray="4 4" />

          <text x={centerX} y={centerY - 5} textAnchor="middle" fill="white/40" fontSize="10" fontWeight="500">UKUPNO</text>
          <text x={centerX} y={centerY + 12} textAnchor="middle" fill="white" fontSize="28" fontWeight="700" fontFamily="monospace">
            {animationProgress >= 1.0 
              ? `${Math.round(sortedParties.reduce((s, p) => s + (p.seats_mean ?? 0), 0))} / ${totalSeats}`
              : `${Math.round(sortedParties.reduce((s, p) => s + (p.animatedPct ?? p.pct * animationProgress), 0))}%`}
          </text>
        </svg>
      </div>

      {/* Party List with votes, bars, seats */}
      <div className="mt-4 space-y-2 overflow-y-auto pr-2 max-h-[60vh]">
        {sortedParties.map((p, i) => {
          const animated = sortedParties.find(ap => ap.short_name === p.short_name);
          const animPct = animated?.animatedPct ?? p.pct * animationProgress;
          const animVotes = animated?.animatedVotes ?? Math.round((p.votes_mean ?? 0) * animationProgress);
          const showMandates = animationProgress >= 1.0;
          
          return (
            <div
              key={p.short_name}
              className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors group"
              style={{ animation: `count-up 0.3s ease-out ${i * 30}ms forwards`, opacity: 0 }}
            >
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: p.color_hex }} />
              <span className="text-xs font-mono text-white/60 w-6 text-right tabular-nums">{p.ballot_number ?? '—'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate flex items-center gap-1.5">
                  {p.short_name}
                  {p.is_minority && <span className="px-1 py-0.5 text-[9px] rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">manjinska</span>}
                  {p.is_governing && <span className="px-1 py-0.5 text-[9px] rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">vlada</span>}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  {/* Vote bar - based on animatedPct */}
                  <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden relative">
                    <div
                      className="h-full rounded-full bg-gradient-to-r"
                      style={{
                        width: `${Math.min(p.pct * animationProgress, 100)}%`,
                        background: `linear-gradient(90deg, ${p.color_hex}CC, ${p.color_hex})`,
                        transition: `width 300ms ease-out`,
                      }}
                    />
                  </div>
                  {/* Absolute votes */}
                  <span className="text-[10px] text-white/60 tabular-nums w-16 text-right font-mono">
                    {Math.round((p.votes_mean ?? 0) * animationProgress).toLocaleString("sr-RS")}
                  </span>
                  {/* Seats - only at 100% */}
                  <span className="text-[10px] text-white/50 tabular-nums w-10 text-right font-mono">
                    {animationProgress >= 1.0 ? Math.round(p.seats_mean ?? 0) : '—'}
                  </span>
                  {/* Percentage */}
                  <span className="text-[10px] text-white/30 tabular-nums w-10 text-right font-mono">
                    {(p.pct * animationProgress).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          );
        })}
        {animationProgress >= 1.0 && (
          <div className="pt-2 border-t border-white/10 flex items-center justify-between text-xs">
            <span className="text-white/50">
              Ukupno mandati: <span className="text-white font-mono">
                {Math.round(sortedParties.reduce((s, p) => s + (p.seats_mean ?? 0), 0))}
              </span> / {totalSeats}
            </span>
            <span className="text-white/40 text-[10px]">
              CI: 95% | Prag: {threshold}% | Manjinski koef: 1.35
            </span>
          </div>
        )}
      </div>
    </div>
  );
}