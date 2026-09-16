"use client";

import type { Election } from "@/lib/types";
import { GOVERNING_LIST, PARTY_ABBR_COLORS } from "@/lib/governing";

function StatusBadge({ status }: { status?: string }) {
  const map: Record<string, { label: string; className: string }> = {
    live: { label: "UŽIVO", className: "bg-red-500/15 text-red-400 border-red-500/30" },
    closed: { label: "ZAVRŠENO", className: "bg-white/10 text-white/60 border-white/15" },
    upcoming: { label: "PREDSTOJI", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  };
  const s = map[status || "upcoming"] ?? map.upcoming;
  return (
    <span className={`text-[10px] font-semibold tracking-wide px-2 py-1 rounded-full border ${s.className} shrink-0`}>
      {status === "live" && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse align-middle" />
      )}
      {s.label}
    </span>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso + "T00:00:00").toLocaleDateString("sr-RS", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function ElectionPicker({
  elections,
  isLoading,
  onPick,
}: {
  elections?: Election[] | null;
  isLoading: boolean;
  onPick: (id: number) => void;
}) {
  return (
    <main className="h-full w-full overflow-y-auto bg-[#0b0d12]">
      <div className="min-h-full w-full max-w-6xl mx-auto flex flex-col items-center justify-center px-5 py-8">
      <img src="/logo.svg" alt="Serbia Election Dashboard" width={44} height={44} className="mb-3" />
      <p className="text-[11px] uppercase tracking-[0.2em] text-white/35 font-medium mb-2">
        Serbia Elections
      </p>
      <h1 className="text-xl sm:text-2xl font-semibold text-white text-center">
        Koje izbore želite da vidite?
      </h1>
      <p className="text-sm text-white/40 mt-2 mb-6 text-center">
        Izaberite izborni ciklus za pregled rezultata po regionima i opštinama.
      </p>

      {isLoading || !elections ? (
        <div className="flex items-center gap-3 text-white/50">
          <span className="w-5 h-5 rounded-full border-2 border-white/15 border-t-white/80 animate-spin" />
          <span className="text-sm">Učitavanje izbora…</span>
        </div>
      ) : elections.length === 0 ? (
        <p className="text-sm text-white/40">Trenutno nema dostupnih izbora.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full">
          {elections.map((e) => {
            const votes = e.total_votes ?? 0;
            const hasData = votes > 0;
            const gov = e.slug ? GOVERNING_LIST[e.slug] ?? null : null;
            return (
              <button
                key={e.id}
                onClick={() => onPick(e.id)}
                className="group text-left rounded-2xl bg-white/[0.04] border border-white/10 p-4 hover:bg-white/[0.07] hover:border-white/25 transition-all hover:-translate-y-0.5 h-full flex flex-col"
              >
                <div className="flex items-center justify-between mb-3">
                  <StatusBadge status={e.status} />
                  <span className="text-white/25 group-hover:text-white/70 group-hover:translate-x-0.5 transition-all text-lg leading-none">
                    →
                  </span>
                </div>
                <p className="text-base font-semibold text-white leading-snug">{e.name}</p>
                <p className="text-xs text-white/40 mt-1 tabular-nums">{formatDate(e.election_date)}</p>
                <div className="flex items-center gap-4 mt-auto pt-3 border-t border-white/10">
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">
                      Vlast
                    </p>
                    <p className="text-sm font-semibold text-white tabular-nums flex items-center gap-1.5 whitespace-nowrap">
                      {gov ? (
                        gov.map((p, i) => (
                          <span key={p} className="inline-flex items-center gap-1 shrink-0">
                            {i > 0 && <span className="text-white/30 font-normal">+</span>}
                            <span
                              className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ background: PARTY_ABBR_COLORS[p] || "#888" }}
                            />
                            <span>{p}</span>
                          </span>
                        ))
                      ) : (
                        <span className="text-white/30">—</span>
                      )}
                    </p>
                  </div>
                  <div className="border-l border-white/10 pl-4">
                    <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">
                      Ukupno glasova
                    </p>
                    <p className="text-sm font-semibold text-white tabular-nums">
                      {hasData ? Number(votes).toLocaleString("sr-RS") : "—"}
                    </p>
                  </div>
                </div>
                <p className="text-[11px] text-white/30 mt-3 min-h-[16px]">
                  {!hasData ? (e.status === "upcoming" ? "Izbori predstoje." : "Još nema unetih rezultata.") : ""}
                </p>
              </button>
            );
          })}
        </div>
      )}
      </div>
    </main>
  );
}
