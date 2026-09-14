"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

// Polukružna raspodela: spolja veći, unutra manji redovi (zbir mora biti 250)
const ROWS = [56, 50, 44, 38, 33, 29];
const RADII = [185, 160, 135, 110, 85, 60];
const CX = 200;
const CY = 200;
const DOT_R = 3;

export default function MandateChart({ electionId }: { electionId: number }) {
  const { data, error, isLoading } = useSWR(
    ["mandates", electionId],
    () => api.mandates(electionId),
    { refreshInterval: 30000 }
  );

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-28 rounded-xl bg-white/[0.04] border border-white/10" />
      </div>
    );
  }
  if (error || !data) return null;

  const seated = data.parties.filter((p) => p.seats > 0);
  const total = seated.reduce((s, p) => s + p.seats, 0);
  if (total === 0) return null;

  // Tačke poređane po veličini stranke, s leva na desno
  const ordered = [...seated].sort((a, b) => b.seats - a.seats || b.votes - a.votes);
  const flat: typeof ordered = [];
  for (const p of ordered) for (let k = 0; k < p.seats; k++) flat.push(p);
  const dots: { x: number; y: number; color: string; name: string }[] = [];
  let cursor = 0;
  ROWS.forEach((count, ri) => {
    const R = RADII[ri];
    for (let i = 0; i < count && cursor < flat.length; i++, cursor++) {
      const party = flat[cursor];
      const angle = count === 1 ? Math.PI / 2 : Math.PI - (i * Math.PI) / (count - 1);
      dots.push({
        x: CX + R * Math.cos(angle),
        y: CY - R * Math.sin(angle),
        color: party.color_hex || "#888",
        name: `${party.short_name || party.name} · ${party.seats}`,
      });
    }
  });

  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">
        Raspodela mandata · {data.total_seats}
      </p>
      <svg viewBox="0 0 400 212" className="w-full h-auto" role="img" aria-label="Polukružni prikaz mandata">
        {dots.map((d, i) => (
          <circle key={i} cx={d.x.toFixed(1)} cy={d.y.toFixed(1)} r={DOT_R} fill={d.color}>
            <title>{d.name}</title>
          </circle>
        ))}
        <text x={CX} y={CY - 8} textAnchor="middle" fill="#fff" fontSize="22" fontWeight="700" className="tabular-nums">
          {total}
        </text>
        <text x={CX} y={CY + 10} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10">
          mandata · većina {Math.floor(data.total_seats / 2) + 1}
        </text>
      </svg>
      <div className="flex flex-col gap-1.5 mt-2">
        {ordered.map((p) => (
          <div key={p.id} className="flex items-center gap-2 min-w-0">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
              style={{ background: p.color_hex || "#888" }}
            />
            <span title={p.name} className="truncate text-xs text-white/70">
              {p.short_name || p.name}
            </span>
            <span className="ml-auto text-xs font-semibold text-white tabular-nums shrink-0">
              {p.seats}
            </span>
            <span className="text-[11px] text-white/35 tabular-nums shrink-0 w-12 text-right">
              {p.pct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-white/30 mt-2">
        {data.official
          ? "Zvanična raspodela mandata."
          : `Projekcija mandata uživo (D'Hondt, cenzus ${data.threshold_pct}%).`}
      </p>
    </div>
  );
}
