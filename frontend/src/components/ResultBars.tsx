import { useState } from "react";
import type { PartyResult } from "@/lib/types";

// Republički cenzus — liste ispod se sklapaju (vredi na državnom nivou,
// ali pomaže pregledu i na nižim nivoima). Do reforme feb. 2020. bio je 5%.
export default function ResultBars({
  results,
  compact = false,
  pastTense = false,
  censusPct = 3,
  governingBallots = [],
  status = "live",
}: {
  results: PartyResult[];
  compact?: boolean;
  // Za završene izbore bedž glasi "Vlast" (vladajuća koalicija) umesto "Vodi"
  pastTense?: boolean;
  censusPct?: number;
  governingBallots?: number[];
  // "Vodi" ima smisla samo dok izbori traju (live), ne za predstojeće
  status?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  if (results.length === 0) {
    return <p className="text-sm text-white/40">Još nema obrađenih rezultata.</p>;
  }

  const leaderPct = results[0]?.pct ?? 0;
  const above = results.filter((r) => r.pct >= censusPct);
  const below = results.filter((r) => r.pct < censusPct);
  const visible = expanded || above.length === 0 ? results : above;
  const isGov = (r: PartyResult) =>
    r.ballot_number != null && governingBallots.includes(r.ballot_number);
  const anyGov = results.some(isGov);

  return (
    <div className="flex flex-col gap-2.5">
      {visible.map((r) => {
        const i = results.indexOf(r);
        const gov = isGov(r);
        // Pobednik po glasovima nije nužno vlast — bedž nosi vladajuća koalicija.
        // "Vodi" samo dok izbori traju (live); za predstojeće nema bedža.
        const badge =
          status === "live" && i === 0 && !pastTense
            ? "Vodi"
            : pastTense && gov
            ? "Vlast"
            : pastTense && !anyGov && i === 0
            ? "Pobedio"
            : null;
        return (
        <div key={r.short_name}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                style={{ background: r.color_hex || "#888" }}
              />
              <span
                title={r.name}
                className={`truncate ${compact ? "text-xs" : "text-sm"} ${
                  i === 0 ? "text-white font-medium" : "text-white/70"
                }`}
              >
                {compact ? r.short_name || r.name : r.name}
              </span>
              {badge && (
                <span
                  className={`text-[10px] uppercase tracking-wide font-semibold shrink-0 ${
                    badge === "Vlast" ? "text-red-400/90" : "text-emerald-400/90"
                  }`}
                >
                  {badge}
                </span>
              )}
            </div>
            <span
              className={`tabular-nums shrink-0 ml-2 ${compact ? "text-xs" : "text-sm"} font-semibold ${
                i === 0 ? "text-white" : "text-white/70"
              }`}
            >
              {r.pct.toFixed(1)}%
            </span>
          </div>
          <div className="bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full rounded-full transition-[width] duration-500 ease-out"
              style={{
                width: `${Math.max(1, (r.pct / (leaderPct || 1)) * 100)}%`,
                background: r.color_hex || "#378ADD",
                opacity: i === 0 ? 1 : 0.55,
              }}
            />
          </div>
          {!compact && (
            <p className="text-[11px] text-white/35 mt-0.5 tabular-nums">
              {r.votes.toLocaleString("sr-RS")} glasova
            </p>
          )}
        </div>
        );
      })}
      {below.length > 0 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          title={`Cenzus od ${censusPct}% važi na republičkom nivou`}
          className="self-start text-[11px] text-white/45 hover:text-white/80 transition-colors mt-0.5"
        >
          {expanded ? "Sakrij ispod cenzusa" : `Prikaži i ispod cenzusa (${censusPct}%) · ${below.length}`}
        </button>
      )}
    </div>
  );
}
