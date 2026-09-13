"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import SerbiaMap from "@/components/SerbiaMap";
import WorldMap from "@/components/WorldMap";
import ResultBars from "@/components/ResultBars";
import MunicipalityPanel from "@/components/MunicipalityPanel";
import { getTier } from "@/lib/colorScale";
import diasporaStations from "../../public/data/diaspora-stations.json";

const ELECTION_ID = 1;
const REFRESH_MS = 30000;

// Isti mapping kao u SerbiaMap - okrug (30) -> RIK region (5)
const OKRUG_TO_RIK: Record<string, string> = {
  "Grad Beograd": "Београдски регион",
  "Severnobački okrug": "Регион Војводине",
  "Srednjebanatski okrug": "Регион Војводине",
  "Severnobanatski okrug": "Регион Војводине",
  "Južnobanatski okrug": "Регион Војводине",
  "Zapadnobački okrug": "Регион Војводине",
  "Južnobački okrug": "Регион Војводине",
  "Sremski okrug": "Регион Војводине",
  Sremski: "Регион Војводине",
  "Zlatiborski okrug": "Регион Шумадије и Западне Србије",
  "Kolubarski okrug": "Регион Шумадије и Западне Србије",
  "Mačvanski okrug": "Регион Шумадије и Западне Србије",
  "Moravički okrug": "Регион Шумадије и Западне Србије",
  "Pomoravski okrug": "Регион Шумадије и Западне Србије",
  "Rasinski okrug": "Регион Шумадије и Западне Србије",
  "Raški okrug": "Регион Шумадије и Западне Србије",
  "Šumadijski okrug": "Регион Шумадије и Западне Србије",
  "Borski okrug": "Регион Јужне и Источне Србије",
  "Braničevski okrug": "Регион Јужне и Источне Србије",
  "Zaječarski okrug": "Регион Јужне и Источне Србије",
  Zaječarski: "Регион Јужне и Источне Србије",
  "Jablanički okrug": "Регион Јужне и Источне Србије",
  "Nišavski okrug": "Регион Јужне и Источне Србије",
  "Pirotski okrug": "Регион Јужне и Источне Србије",
  "Podunavski okrug": "Регион Јужне и Источне Србије",
  "Pčinjski okrug": "Регион Јужне и Источне Србије",
  "Toplički okrug": "Регион Јужне и Источне Србије",
  "Kosovski okrug": "Регион Косово и Метохија",
  Kosovski: "Регион Косово и Метохија",
  "Pećki okrug": "Регион Косово и Метохија",
  Pećki: "Регион Косово и Метохија",
  "Prizrenski okrug": "Регион Косово и Метохија",
  Prizrenski: "Регион Косово и Метохија",
  "Kosovsko-mitrovački okrug": "Регион Косово и Метохија",
  "Kosovsko-pomoravski okrug": "Регион Косово и Метохија",
};

type ViewMode = "serbia" | "diaspora";

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<ViewMode>("serbia");
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedMunicipalityId, setSelectedMunicipalityId] = useState<number | null>(null);
  const [selectedDiasporaStation, setSelectedDiasporaStation] = useState<number | null>(null);

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

  const regionMunicipalities = useMemo(() => {
    if (!selectedRegion || !municipalities) return [];
    // direktan match (demo podaci)
    let filtered = municipalities.filter((m) => m.region === selectedRegion);
    if (filtered.length === 0) {
      const rik = OKRUG_TO_RIK[selectedRegion];
      if (rik) filtered = municipalities.filter((m) => m.region === rik);
    }
    return filtered;
  }, [municipalities, selectedRegion]);

  const selectedRegionData = useMemo(() => {
    if (!selectedRegion || !regions) return null;
    let r = regions.find((x) => x.region === selectedRegion);
    if (r) return r;
    const rik = OKRUG_TO_RIK[selectedRegion];
    if (rik) return regions.find((x) => x.region === rik) ?? null;
    return null;
  }, [regions, selectedRegion]);

  const diasporaRegion = useMemo(
    () => regions?.find((r) => r.region === "Inostranstvo") ?? null,
    [regions]
  );

  // grupiši dijaspora stanice po državi za side panel
  const diasporaByCountry = useMemo(() => {
    const map = new Map<string, typeof diasporaStations>();
    for (const s of diasporaStations as unknown as { id: number; name: string; city: string; country: string; lat: number; lon: number }[]) {
      const arr = map.get(s.country) || [];
      arr.push(s);
      map.set(s.country, arr);
    }
    return Array.from(map.entries()).sort((a, b) => b[1].length - a[1].length);
  }, []);

  const selectedDiasporaStationData = useMemo(
    () => (diasporaStations as unknown as { id: number; name: string; city: string; country: string }[]).find((s) => s.id === selectedDiasporaStation) ?? null,
    [selectedDiasporaStation]
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
            {viewMode === "diaspora"
              ? "Dijaspora · 81 biračko mesto u 35 država"
              : selectedRegion
              ? selectedRegion
              : "Rezultati uživo · klik na okrug za detalje"}
          </p>
        </div>

        <StatusBadge status={summary?.election.status} />

        {/* View toggle */}
        <div className="flex items-center rounded-full bg-white/[0.06] border border-white/10 p-1 ml-4">
          <button
            onClick={() => setViewMode("serbia")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              viewMode === "serbia" ? "bg-white text-black" : "text-white/60 hover:text-white"
            }`}
          >
            Srbija
          </button>
          <button
            onClick={() => {
              setViewMode("diaspora");
              setSelectedRegion(null);
              setSelectedMunicipalityId(null);
            }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
              viewMode === "diaspora" ? "bg-white text-black" : "text-white/60 hover:text-white"
            }`}
          >
            Dijaspora
            <span className={`text-[10px] px-1 py-0.5 rounded font-bold ${viewMode === "diaspora" ? "bg-black/10" : "bg-white/10"}`}>81</span>
          </button>
        </div>

        <div className="flex items-center gap-6 ml-auto">
          <Metric label="Obrađeno" value={summary ? `${summary.processed_pct.toFixed(1)}%` : "—"} />
          <Metric label="Izlaznost" value={summary ? `${summary.turnout_pct.toFixed(1)}%` : "—"} />
          {summary && viewMode === "serbia" && (
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
          {viewMode === "serbia" ? (
            regions ? (
              <SerbiaMap
                regions={regions.filter((r) => r.region !== "Inostranstvo" && r.region !== "Заводи за извршење кривичних санкција")}
                municipalities={municipalities}
                selectedRegion={selectedRegion}
                onSelectRegion={(region) => {
                  setSelectedRegion(region);
                  setSelectedMunicipalityId(null);
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-white/30 text-sm">Učitavanje mape…</div>
            )
          ) : (
            <WorldMap
              diasporaRegion={diasporaRegion}
              selectedStationId={selectedDiasporaStation}
              onSelectStation={setSelectedDiasporaStation}
            />
          )}
        </section>

        {/* Sidebar */}
        <aside className="w-[380px] shrink-0 border-l border-white/10 bg-[#0e1117] flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto hide-scrollbar px-5 py-5 flex flex-col gap-5">
            {viewMode === "serbia" ? (
              <>
                {/* Nacionalni pregled */}
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-3">Ukupni rezultati</p>
                  {summary ? (
                    <>
                      <div className="grid grid-cols-3 gap-2 mb-4">
                        <MiniStat label="Obrađeno" value={`${summary.processed_pct.toFixed(1)}%`} />
                        <MiniStat label="Izlaznost" value={`${summary.turnout_pct.toFixed(1)}%`} />
                        <MiniStat label="Biračkih mesta" value={`${summary.processed_pct.toFixed(0)}%`} />
                      </div>
                      <ResultBars results={summary.results} />
                      {summary.results[0] && (
                        <p className="text-[11px] text-white/35 mt-2 tabular-nums">
                          Ukupno glasova: {summary.results.reduce((s, r) => s + r.votes, 0).toLocaleString("sr-RS")} · {summary.results[0].short_name} +
                          {(summary.results[0].pct - (summary.results[1]?.pct ?? 0)).toFixed(1)}pp prednosti
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-white/30">Učitavanje…</p>
                  )}
                </div>

                {selectedRegion && selectedRegionData && (
                  <div className="border-t border-white/10 pt-5">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium">Okrug</p>
                        <p className="text-[15px] font-semibold text-white leading-tight">{selectedRegion}</p>
                        <p className="text-[11px] text-white/40 tabular-nums">
                          {selectedRegionData.processed_stations}/{selectedRegionData.total_stations} BM · {selectedRegionData.processed_pct.toFixed(0)}% obrađeno
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
                          {getTier(selectedRegionData.margin_pct, true) === "secure" ? "SIGURNO" : getTier(selectedRegionData.margin_pct, true) === "lean" ? "UMERENO" : "NEIZVESNO"}
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
                        <span className="w-3 h-3 rounded-full shrink-0" style={{ background: selectedRegionData.leader.color_hex || "#888" }} />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-white truncate">{selectedRegionData.leader.short_name} vodi</p>
                          <p className="text-[11px] text-white/50 truncate">{selectedRegionData.leader.name}</p>
                        </div>
                        <span className="ml-auto text-sm font-semibold text-white tabular-nums">{selectedRegionData.leader.pct.toFixed(1)}%</span>
                      </div>
                    )}

                    <ResultBars results={selectedRegionData.results} compact />

                    <div className="mt-4">
                      <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">
                        Opštine u okrugu ({regionMunicipalities.length})
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
                                  isSelected ? "bg-white/10 border-white/20" : "bg-white/[0.03] border-white/10 hover:bg-white/[0.06] hover:border-white/15"
                                }`}
                              >
                                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: m.leader?.color_hex || "#333" }} />
                                <div className="min-w-0 flex-1">
                                  <p className="text-xs text-white truncate leading-tight">{m.name}</p>
                                  <p className="text-[11px] text-white/40 tabular-nums">
                                    {m.processed_pct.toFixed(0)}% obrađeno · {m.turnout_pct.toFixed(1)}% izlaznost
                                  </p>
                                </div>
                                <div className="text-right shrink-0">
                                  <p className="text-xs font-semibold text-white tabular-nums">{m.leader ? `${m.leader.pct.toFixed(1)}%` : "—"}</p>
                                  <p className={`text-[10px] font-medium ${tier === "secure" ? "text-emerald-300" : tier === "lean" ? "text-amber-300" : tier === "tossup" ? "text-white/50" : "text-white/30"}`}>
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
                      Klikni na okrug za detalj. Boje: <span className="text-white/60">tamno ≥10%</span>, <span className="text-white/60">srednje 5–10%</span>,{" "}
                      <span className="text-white/60">šrafirano &lt;5%</span>. Zaključan prikaz opština dok ne izađeš.
                    </p>
                  </div>
                )}
              </>
            ) : (
              <>
                {/* Dijaspora side panel */}
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-3">Inostranstvo</p>
                  {diasporaRegion ? (
                    <>
                      <div className="rounded-xl bg-gradient-to-br from-blue-600/20 to-indigo-600/20 border border-blue-500/20 p-4 mb-4">
                        <p className="text-xs text-white/60 mb-1">Ukupno dijaspora</p>
                        <p className="text-2xl font-bold text-white tabular-nums">{diasporaRegion.processed_stations}/{diasporaRegion.total_stations}</p>
                        <p className="text-[11px] text-white/50">biračkih mesta · {diasporaRegion.processed_pct.toFixed(0)}% obrađeno · {diasporaRegion.turnout_pct.toFixed(1)}% izlaznost</p>
                        {diasporaRegion.leader && (
                          <div className="mt-3 flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ background: diasporaRegion.leader.color_hex }} />
                            <span className="text-xs text-white">{diasporaRegion.leader.short_name} {diasporaRegion.leader.pct.toFixed(1)}%</span>
                            <span className="text-[11px] text-white/40">+{diasporaRegion.margin_pct.toFixed(1)}pp</span>
                          </div>
                        )}
                      </div>
                      <ResultBars results={diasporaRegion.results} compact />
                      <p className="text-[11px] text-white/30 mt-2">
                        Region: <span className="text-white/60">Inostranstvo (101)</span> · Opština: Inostranstvo (198) · 81 ambasada/konzulat kao biračka mesta. Kao na RIK-u: <code className="text-white/50">region=101&municipality=198&election_station=183514</code>
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-white/30">Nema podataka za Inostranstvo (potrebno pokrenuti bootstrap za 2023/2026)</p>
                  )}
                </div>

                {selectedDiasporaStationData && (
                  <div className="border-t border-white/10 pt-4">
                    <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">Biračko mesto</p>
                    <div className="rounded-xl bg-white/[0.04] border border-white/10 p-4">
                      <p className="text-sm font-semibold text-white">{selectedDiasporaStationData.city}</p>
                      <p className="text-xs text-white/60">{selectedDiasporaStationData.name}</p>
                      <p className="text-[11px] text-white/35 mt-1">RIK ID: {selectedDiasporaStationData.id} · {selectedDiasporaStationData.country}</p>
                      <p className="text-[11px] text-white/30 mt-2">Detaljni rezultati po biračkom mestu dolaze preko <code className="text-white/40">GET /elections/{ELECTION_ID}/polling-stations/{selectedDiasporaStation}</code> nakon bootstrap-a.</p>
                    </div>
                  </div>
                )}

                <div className="border-t border-white/10 pt-4">
                  <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-2">Ambasade po državama ({diasporaStations.length})</p>
                  <div className="flex flex-col gap-3 max-h-[320px] overflow-y-auto hide-scrollbar pr-1">
                    {diasporaByCountry.map(([country, stations]) => (
                      <div key={country}>
                        <p className="text-[11px] font-medium text-white/50 mb-1">
                          {country} · {stations.length} {stations.length === 1 ? "mesto" : "mesta"}
                        </p>
                        <div className="flex flex-col gap-1">
                          {stations.map((s) => (
                            <button
                              key={s.id}
                              onClick={() => setSelectedDiasporaStation(s.id === selectedDiasporaStation ? null : s.id)}
                              className={`text-left rounded-lg border px-2.5 py-1.5 text-xs transition-colors truncate ${
                                selectedDiasporaStation === s.id
                                  ? "bg-white/10 border-white/20 text-white"
                                  : "bg-white/[0.03] border-white/10 text-white/70 hover:bg-white/[0.06] hover:text-white"
                              }`}
                            >
                              {s.city} — {s.name.slice(0, 48)}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-white/10 pt-4">
                  <p className="text-[11px] leading-relaxed text-white/30">
                    Globalna mapa prikazuje sva 81 biračka mesta iz RIK-a za 2023 (region 101, opština 198). Svaka tačka je ambasada/konzulat. Boja prati nacionalnog lidera, a izbor na tačku otvara detalje.
                  </p>
                </div>
              </>
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
      {status === "live" && <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5 animate-pulse align-middle" />}
      {s.label}
    </span>
  );
}
