"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

// Polukružna raspodela kao u srpskim medijima: 10 redova sa ravnomernom
// gustinom (svako mesto ~jednak luk), krupnije tačke. Zbir redova je 250.
const ROWS = [39, 36, 33, 30, 27, 23, 20, 17, 14, 11];
const RADII = [185, 170, 155, 140, 125, 110, 95, 80, 65, 50];
const CX = 200;
const CY = 200;
const DOT_R = 4.5;

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

  // Standardni parlamentarni dijagram (kao u Skupštini / na Vikipediji):
  // stranke su klinovi od centra ka ivici — najveća kreće s leve strane,
  // a svaki red seče sve stranke proporcionalno. Zato se pozicije sortiraju
  // po uglu (pa po poluprečniku), a ne pune red-po-red celim strankama.
  const ordered = [...seated].sort((a, b) => b.seats - a.seats || b.votes - a.votes);
  const flat: typeof ordered = [];
  for (const p of ordered) for (let k = 0; k < p.seats; k++) flat.push(p);
  type Pos = { angle: number; R: number };
  const positions: Pos[] = [];
  ROWS.forEach((count, ri) => {
    for (let i = 0; i < count; i++) {
      positions.push({
        angle: count === 1 ? Math.PI / 2 : Math.PI - (i * Math.PI) / (count - 1),
        R: RADII[ri],
      });
    }
  });
  positions.sort((a, b) => b.angle - a.angle || b.R - a.R);
  const dots = positions.slice(0, flat.length).map((p, k) => {
    const party = flat[k];
    return {
      x: CX + p.R * Math.cos(p.angle),
      y: CY - p.R * Math.sin(p.angle),
      color: party.color_hex || "#888",
      name: `${party.short_name || party.name} · ${party.seats}`,
    };
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
