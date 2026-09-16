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

export type PrimeMinister = { name: string; party?: string | null; period?: string | null };

export default function MandateChart({
  electionId,
  governingBallots = [],
  primeMinister = null,
  primeMinisterParty = null,
  primeMinisters = null,
  partyLabels = {},
}: {
  electionId: number;
  governingBallots?: number[];
  primeMinister?: string | null;
  primeMinisterParty?: string | null;
  primeMinisters?: PrimeMinister[] | null;
  partyLabels?: Record<number, string>;
}) {
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
  const gov = new Set(
    data.parties.filter((p) => governingBallots.includes(p.ballot_number ?? -1)).map((p) => p.id)
  );
  const placed = positions.slice(0, flat.length);
  const dots = placed.map((p, k) => {
    const party = flat[k];
    return {
      x: CX + p.R * Math.cos(p.angle),
      y: CY - p.R * Math.sin(p.angle),
      angle: p.angle,
      R: p.R,
      color: party.color_hex || "#888",
      name: `${party.short_name || party.name} · ${party.seats}`,
      governing: gov.has(party.id),
    };
  });

  // Grupni okvir(i) oko vladajućih tačaka: prstenasti sektori po
  // uglovno-susednim grupama (vlast ne mora biti u jednom komadu).
  const pt = (a: number, r: number): [number, number] => [
    CX + r * Math.cos(a),
    CY - r * Math.sin(a),
  ];
  const sectorPath = (a0: number, a1: number, r0: number, r1: number) => {
    const [x0o, y0o] = pt(a0, r1);
    const [x1o, y1o] = pt(a1, r1);
    const [x1i, y1i] = pt(a1, r0);
    const [x0i, y0i] = pt(a0, r0);
    const large = a1 - a0 > Math.PI ? 1 : 0;
    return (
      `M ${x0o.toFixed(1)} ${y0o.toFixed(1)} ` +
      `A ${r1.toFixed(1)} ${r1.toFixed(1)} 0 ${large} 0 ${x1o.toFixed(1)} ${y1o.toFixed(1)} ` +
      `L ${x1i.toFixed(1)} ${y1i.toFixed(1)} ` +
      `A ${r0.toFixed(1)} ${r0.toFixed(1)} 0 ${large} 1 ${x0i.toFixed(1)} ${y0i.toFixed(1)} Z`
    );
  };
  const govSectors = (() => {
    const gd = dots.filter((d) => d.governing).sort((a, b) => a.angle - b.angle);
    if (gd.length === 0) return [] as string[];
    const GAP = 0.12;
    const runs: typeof gd[] = [[gd[0]]];
    for (const d of gd.slice(1)) {
      const last = runs[runs.length - 1];
      if (d.angle - last[last.length - 1].angle > GAP) runs.push([d]);
      else last.push(d);
    }
    return runs.map((run) => {
      const as = run.map((d) => d.angle);
      const rs = run.map((d) => d.R);
      const a0 = Math.max(0, Math.min(...as) - 0.05);
      const a1 = Math.min(Math.PI, Math.max(...as) + 0.05);
      const r0 = Math.max(16, Math.min(...rs) - 11);
      const r1 = Math.max(...rs) + 11;
      return sectorPath(a0, a1, r0, r1);
    });
  })();

  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">
        Raspodela mandata · {data.total_seats}
      </p>
      <svg viewBox="0 0 400 252" className="w-full h-auto" role="img" aria-label="Polukružni prikaz mandata">
        {govSectors.map((d, i) => (
          <path
            key={`gov-${i}`}
            d={d}
            fill="rgba(248,113,113,0.07)"
            stroke="#f87171"
            strokeWidth={1.6}
          >
            <title>Vladajuća koalicija</title>
          </path>
        ))}
        {dots.map((d, i) => (
          <circle key={i} cx={d.x.toFixed(1)} cy={d.y.toFixed(1)} r={DOT_R} fill={d.color}>
            <title>{d.name}{d.governing ? " (vlast)" : ""}</title>
          </circle>
        ))}
        {/* Ukupan broj ispod luka, u praznoj zoni — bez preklapanja sa tačkama */}
        <text x={CX} y={CY + 32} textAnchor="middle" fill="#fff" fontSize="24" fontWeight="800" className="tabular-nums">
          {total}
        </text>
        <text x={CX} y={CY + 48} textAnchor="middle" fill="rgba(255,255,255,0.45)" fontSize="9.5" letterSpacing="2">
          MANDATA · VEĆINA {Math.floor(data.total_seats / 2) + 1}
        </text>
      </svg>
      {primeMinisters && primeMinisters.length > 0 ? (
        <p className="text-[11px] text-white/45 mt-2 leading-relaxed">
          Premijer{primeMinisters.length > 1 ? "i" : ""}:{" "}
          {primeMinisters.map((pm, i) => (
            <span key={pm.name}>
              {i > 0 && <span className="text-white/30"> → </span>}
              <span className="text-white/80 font-medium">{pm.name}</span>
              {pm.period && <span className="text-white/35 tabular-nums"> ({pm.period})</span>}
            </span>
          ))}
        </p>
      ) : (
        primeMinister && (
          <p className="text-[11px] text-white/45 mt-2">
            Premijer: <span className="text-white/80 font-medium">{primeMinister}</span>
            {primeMinisterParty && <span className="text-white/35"> ({primeMinisterParty})</span>}
          </p>
        )
      )}
      <div className="flex flex-col gap-1.5 mt-2">
        {ordered.map((p) => (
          <div key={p.id} className="flex items-center gap-2 min-w-0">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
              style={{
                background: p.color_hex || "#888",
                outline: gov.has(p.id) ? "1.5px solid #f87171" : "none",
                outlineOffset: 1,
              }}
            />
            <div className="flex flex-col min-w-0 leading-tight">
              <span
                title={p.name}
                className={`truncate text-xs text-white/70 ${
                  gov.has(p.id) ? "underline decoration-red-400/80 underline-offset-[3px]" : ""
                }`}
              >
                {p.short_name || p.name}
              </span>
              {partyLabels[p.ballot_number ?? -1] && (
                <span className="truncate text-[10px] text-white/35">
                  {partyLabels[p.ballot_number ?? -1]}
                </span>
              )}
            </div>
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
        {gov.size > 0 && " Crveni okvir = vladajuća koalicija."}
      </p>
    </div>
  );
}
