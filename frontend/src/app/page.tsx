"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import SerbiaMap from "@/components/SerbiaMap";
import ResultBars from "@/components/ResultBars";
import MunicipalityPanel from "@/components/MunicipalityPanel";

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
          <p className="text-[11px] text-white/40">Rezultati uživo</p>
        </div>

        <StatusBadge status={summary?.election.status} />

        <div className="flex items-center gap-5 ml-auto">
          <Metric label="Obrađeno" value={summary ? `${summary.processed_pct.toFixed(1)}%` : "—"} />
          <Metric label="Izlaznost" value={summary ? `${summary.turnout_pct.toFixed(1)}%` : "—"} />
        </div>
      </header>

      {error && (
        <div className="mx-5 mt-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs px-3 py-2 shrink-0">
          Ne mogu da se povežem sa API-jem ({process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}).
          Proveri da li backend radi i da li je baza napunjena podacima.
        </div>
      )}

      {/* Main content: map + sidebar, fills remaining height, no page scroll */}
      <div className="flex flex-1 min-h-0">
        {/* Map area */}
        <section className="relative flex-1 min-w-0 bg-[#0b0d12]">
          {regions ? (
            <SerbiaMap
              regions={regions}
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

          {/* Legend */}
          <div className="absolute bottom-3 right-3 rounded-xl bg-black/60 backdrop-blur border border-white/10 px-3 py-2 flex items-center gap-3">
            {summary?.results.slice(0, 4).map((r) => (
              <div key={r.short_name} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ background: r.color_hex || "#888" }}
                />
                <span className="text-[10px] text-white/60">{r.short_name}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Sidebar */}
        <aside className="w-[340px] shrink-0 border-l border-white/10 bg-[#0e1117] flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto hide-scrollbar px-4 py-4 flex flex-col gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">
                Ukupni rezultati
              </p>
              {summary ? <ResultBars results={summary.results} /> : (
                <p className="text-sm text-white/30">Učitavanje…</p>
              )}
            </div>

            {selectedRegion && (
              <div className="border-t border-white/10 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium">
                    {selectedRegion}
                  </p>
                  <button
                    onClick={() => {
                      setSelectedRegion(null);
                      setSelectedMunicipalityId(null);
                    }}
                    className="text-[11px] text-white/40 hover:text-white/70"
                  >
                    Poništi
                  </button>
                </div>

                {selectedRegionData && (
                  <div className="mb-3">
                    <ResultBars results={selectedRegionData.results} compact />
                  </div>
                )}

                <p className="text-[11px] text-white/35 mb-2">Opštine</p>
                <div className="flex flex-wrap gap-1.5">
                  {regionMunicipalities.map((m) => {
                    const pct = m.total_stations > 0 ? Math.round((100 * m.processed_stations) / m.total_stations) : 0;
                    const isSelected = selectedMunicipalityId === m.id;
                    return (
                      <button
                        key={m.id}
                        onClick={() => setSelectedMunicipalityId(m.id)}
                        className={`px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
                          isSelected
                            ? "border-white/60 bg-white/10 text-white"
                            : "border-white/10 text-white/60 hover:border-white/30 hover:text-white/90"
                        }`}
                      >
                        {m.name} · {pct}%
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {selectedMunicipalityId && (
              <div className="border-t border-white/10 pt-4">
                <MunicipalityPanel electionId={ELECTION_ID} municipalityId={selectedMunicipalityId} />
              </div>
            )}

            {!selectedRegion && (
              <p className="text-[11px] text-white/30 border-t border-white/10 pt-4">
                Klikni na okrug na mapi da vidiš opštine i detaljne rezultate.
              </p>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">{label}</p>
      <p className="text-sm font-semibold text-white tabular-nums leading-none">{value}</p>
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
