"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import SerbiaMap from "@/components/SerbiaMap";
import ResultBars from "@/components/ResultBars";
import MunicipalityPanel from "@/components/MunicipalityPanel";
import { getTier } from "@/lib/colorScale";

const ELECTION_ID = 1;
const REFRESH_MS = 30000;

export default function Dashboard() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedMunicipalityId, setSelectedMunicipalityId] = useState<number | null>(null);

  const { data: summary, error: summaryError } = useSWR(
    ["summary", ELECTION_ID],
    () => api.summary(ELECTION_ID),
    { refreshInterval: REFRESH_MS }
  );

  const { data: regions, error: regionsError } = useSWR(
    ["regions", ELECTION_ID],
    () => api.regions(ELECTION_ID),
    { refreshInterval: REFRESH_MS }
  );

  const { data: municipalities, error: municipalitiesError } = useSWR(
    ["municipalities", ELECTION_ID],
    () => api.municipalities(ELECTION_ID),
    { refreshInterval: REFRESH_MS }
  );

  const error = summaryError || municipalitiesError || regionsError;

  const regionMunicipalities = useMemo(
    () => (selectedRegion ? municipalities?.filter((m) => m.region === selectedRegion) ?? [] : []),
    [municipalities, selectedRegion]
  );

  const selectedRegionData = useMemo(
    () => regions?.find((r) => r.region === selectedRegion) ?? null,
    [regions, selectedRegion]
  );

  return (
    <main className="flex flex-col h-full w-full">
      {/* Top bar */}
      <header className="flex items-center gap-4 px-5 py-3 border-b border-white/10 bg-[#0e1117] shrink-0">
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold text-white truncate">
            {summary?.election.name || "Izbori"}
          </h1>
          <p className="text-[11px] text-white/40">
            {selectedRegion ? selectedRegion : "Rezultati uživo · klik na okrug za detalje"}
          </p>
        </div>

        <StatusBadge status={summary?.election.status} />

        <div className="flex items-center gap-6 ml-auto">
          <Metric label="Obrađeno" value={summary ? `${summary.processed_pct.toFixed(1)}%` : "—"} sub={summary ? `${summary.election ? "" : ""}` : undefined} />
          <Metric label="Izlaznost" value={summary ? `${summary.turnout_pct.toFixed(1)}%` : "—"} />
          {summary && (
            <div className="hidden sm:flex items-center gap-2 text-[11px] text-white/35 border-l border-white/10 pl-6">
              <span className="tabular-nums">{summary.results[0]?.short_name || ""} vodi</span>
            </div>
          )}
        </div>
      </header>

      {error && (
        <div className="mx-5 mt-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs px-3 py-2 shrink-0">
          Ne mogu da se povežem sa API-jem ({process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}).
          Proveri da li backend radi i da li je baza napunjena podacima.
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Map */}
        <section className="relative flex-1 min-w-0 bg-[#0b0d12]">
          {regions ? (
            <SerbiaMap
              regions={regions}
              municipalities={municipalities}
              selectedRegion={selectedRegion}
              onSelectRegion={(region) => {
                setSelectedRegion(region);
                setSelectedMunicipalityId(null);
              }}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-white/30 text-sm">
              Učitavanje mape…
            </div>
          )}
        </section>

        {/* Sidebar - više informacija */}
        <aside className="w-[380px] shrink-0 border-l border-white/10 bg-[#0e1117] flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto hide-scrollbar px-5 py-5 flex flex-col gap-5">
            {/* Nacionalni pregled */}
            <div>
              <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-3">
                Ukupni rezultati
              </p>
              {summary ? (
                <>
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <MiniStat label="Obrađeno" value={`${summary.processed_pct.toFixed(1)}%`} />
                    <MiniStat label="Izlaznost" value={`${summary.turnout_pct.toFixed(1)}%`} />
                    <MiniStat
                      label="Biračkih mesta"
                      value={`${summary.results.length ? summary.processed_pct.toFixed(0) : "—"}%`}
                    />
                  </div>
                  <ResultBars results={summary.results} />
                  {summary.results[0] && (
                    <p className="text-[11px] text-white/35 mt-2 tabular-nums">
                      Ukupno glasova:{" "}
                      {summary.results.reduce((s, r) => s + r.votes, 0).toLocaleString("sr-RS")}
                      {" · "}
                      {summary.results[0].short_name} +{(
                        summary.results[0].pct - (summary.results[1]?.pct ?? 0)
                      ).toFixed(1)}
                      pp prednosti
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm text-white/30">Učitavanje…</p>
              )}
            </div>

            {/* Region detalji - bez Ponisti */}
            {selectedRegion && selectedRegionData && (
              <div className="border-t border-white/10 pt-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium">
                      Okrug
                    </p>
                    <p className="text-[15px] font-semibold text-white leading-tight">
                      {selectedRegion}
                    </p>
                    <p className="text-[11px] text-white/40 tabular-nums">
                      {selectedRegionData.processed_stations}/{selectedRegionData.total_stations} BM ·{" "}
                      {selectedRegionData.processed_pct.toFixed(0)}% obrađeno
                    </p>
                  </div>
                  {selectedRegionData.leader && (
                    <span
                      className={`text-[10px] px-2 py-1 rounded-full border font-semibold tracking-wide shrink-0 ${
                        getTier(selectedRegionData.margin_pct, true) === "secure"
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                          : getTier(selectedRegionData.margin_pct, true) === "lean"
                          ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                          : "bg-white/10 text-white/70 border-white/15"
                      }`}
                    >
                      {getTier(selectedRegionData.margin_pct, true) === "secure"
                        ? "SIGURNO"
                        : getTier(selectedRegionData.margin_pct, true) === "lean"
                        ? "UMERENO"
                        : "NEIZVESNO"}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 mb-3">
                  <MiniStat label="Obrađeno" value={`${selectedRegionData.processed_pct.toFixed(0)}%`} />
                  <MiniStat label="Izlaznost" value={`${selectedRegionData.turnout_pct.toFixed(1)}%`} />
                  <MiniStat label="Prednost" value={`+${selectedRegionData.margin_pct.toFixed(1)}pp`} />
                </div>

                {selectedRegionData.leader && (
                  <div className="rounded-lg bg-white/[0.04] border border-white/10 px-3 py-2.5 mb-3 flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ background: selectedRegionData.leader.color_hex || "#888" }}
                    />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-white truncate">
                        {selectedRegionData.leader.short_name} vodi
                      </p>
                      <p className="text-[11px] text-white/50 truncate">{selectedRegionData.leader.name}</p>
                    </div>
                    <span className="ml-auto text-sm font-semibold text-white tabular-nums">
                      {selectedRegionData.leader.pct.toFixed(1)}%
                    </span>
                  </div>
                )}

                <ResultBars results={selectedRegionData.results} compact />

                <div className="mt-4">
                  <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">
                    Opštine u okrugu ({regionMunicipalities.length})
                  </p>
                  <p className="text-[11px] text-white/30 mb-2">
                    Mapa prikazuje opštinske granice sa nijansiranim bojama po margini.
                  </p>
                  <div className="flex flex-col gap-1.5 max-h-[220px] overflow-y-auto hide-scrollbar pr-1">
                    {regionMunicipalities
                      .slice()
                      .sort((a, b) => b.margin_pct - a.margin_pct)
                      .map((m) => {
                        const tier = getTier(m.margin_pct, !!m.leader);
                        const isSelected = selectedMunicipalityId === m.id;
                        return (
                          <button
                            key={m.id}
                            onClick={() => setSelectedMunicipalityId(isSelected ? null : m.id)}
                            className={`text-left rounded-lg border px-3 py-2 flex items-center gap-2 transition-colors ${
                              isSelected
                                ? "bg-white/10 border-white/20"
                                : "bg-white/[0.03] border-white/10 hover:bg-white/[0.06] hover:border-white/15"
                            }`}
                          >
                            <span
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ background: m.leader?.color_hex || "#333" }}
                            />
                            <div className="min-w-0 flex-1">
                              <p className="text-xs text-white truncate leading-tight">{m.name}</p>
                              <p className="text-[11px] text-white/40 tabular-nums">
                                {m.processed_pct.toFixed(0)}% obrađeno · {m.turnout_pct.toFixed(1)}% izlaznost
                              </p>
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-xs font-semibold text-white tabular-nums">
                                {m.leader ? `${m.leader.pct.toFixed(1)}%` : "—"}
                              </p>
                              <p
                                className={`text-[10px] font-medium ${
                                  tier === "secure"
                                    ? "text-emerald-300"
                                    : tier === "lean"
                                    ? "text-amber-300"
                                    : tier === "tossup"
                                    ? "text-white/50"
                                    : "text-white/30"
                                }`}
                              >
                                {tier === "secure" ? "Sigurno" : tier === "lean" ? "Umereno" : tier === "tossup" ? "Neizv." : "—"}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                  </div>
                </div>
              </div>
            )}

            {selectedMunicipalityId && (
              <div className="border-t border-white/10 pt-5">
                <MunicipalityPanel electionId={ELECTION_ID} municipalityId={selectedMunicipalityId} />
              </div>
            )}

            {!selectedRegion && (
              <div className="border-t border-white/10 pt-4">
                <p className="text-[11px] leading-relaxed text-white/30">
                  Klikni na okrug na mapi za detalj. Boje pokazuju marginu pobednika:{" "}
                  <span className="text-white/60">tamno ≥10%</span>,{" "}
                  <span className="text-white/60">srednje 5–10%</span>,{" "}
                  <span className="text-white/60">šrafirano &lt;5%</span> (neizvesno). Kad je okrug izabran, mapa je zaključana i prikazuje opštine unutar njega.
                </p>
              </div>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="text-right">
      <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">{label}</p>
      <p className="text-sm font-semibold text-white tabular-nums leading-none">{value}</p>
      {sub && <p className="text-[10px] text-white/30">{sub}</p>}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.04] border border-white/10 px-2.5 py-2">
      <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">{label}</p>
      <p className="text-xs font-semibold text-white tabular-nums">{value}</p>
    </div>
  );
}

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
