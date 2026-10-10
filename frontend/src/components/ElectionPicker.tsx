"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { GOVERNING_LIST, PARTY_ABBR_COLORS } from "@/lib/governing";
import { formatDate } from "@/lib/display";
import SimulationMandates from "./SimulationMandates";
import { PartyData, SimulationResponse, CountingPath } from "@/lib/types";

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

type ElectionPickerProps = {
  elections?: import("@/lib/types").Election[] | null;
  isLoading: boolean;
  onPick: (id: number) => void;
  upcomingElections?: import("@/lib/types").Election[];
};

export default function ElectionPicker({
  elections,
  isLoading,
  onPick,
  upcomingElections = [],
}: ElectionPickerProps) {
  const router = useRouter();
  const [simMode, setSimMode] = useState<{ 
    electionId: number | null; 
    running: boolean; 
    progress: number; 
    stepIndex: number;
    speed: number; 
    nSimulations: number;
    turnoutOverride: number | null; // user override for prior mean
  }>({
    electionId: null,
    running: false,
    progress: 0,
    stepIndex: 0,
    speed: 1,
    nSimulations: 500,
    turnoutOverride: null,
  });
  
  // Use refs for mutable data to avoid glitchy re-renders
  const simDataRef = useRef<PartyData[]>([]);
  const countingPathRef = useRef<CountingPath | null>(null);
  const [simData, setSimData] = useState<PartyData[]>([]);
  const [countingPath, setCountingPath] = useState<CountingPath | null>(null);
  const [nationalData, setNationalData] = useState<SimulationResponse['metadata']['national'] | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const animationRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const upcoming = upcomingElections?.filter((e) => e.status === "upcoming") ?? [];
  const selectedElection = simMode.electionId
    ? elections?.find((e) => e.id === simMode.electionId)
    : null;

  const fetchSimulationData = useCallback(async (eid: number) => {
    setSimLoading(true);
    setSimError(null);
    abortRef.current = new AbortController();
    
    try {
      const turnoutPrior = simMode.turnoutOverride ?? 62; // Faktor plus 62%, BIRODI 64%
      const res = await api.simulation.run({
        election_id: eid,
        n_simulations: simMode.nSimulations,
        threshold: 3,
        total_seats: 250,
        turnout: turnoutPrior,
        polls: [],
        odds: [],
      });
      
      if (res.parties) {
        const partyData = res.parties.map((p: any) => ({
          short_name: p.short_name,
          color_hex: p.color_hex,
          pct: p.vote_share_mean,
          votes_mean: p.votes_mean,
          seats: p.seats_mean || 0,
          is_governing: p.is_governing,
          ballot_number: p.ballot_number,
          is_minority: p.is_minority,
          animatedSeats: 0,
        }));
        simDataRef.current = partyData;
        setSimData(partyData);
        setCountingPath(res.metadata.counting_path || null);
        countingPathRef.current = res.metadata.counting_path || null;
        setNationalData(res.metadata.national || null);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error("Failed to fetch simulation data:", err);
        setSimError("Greška pri učitavanju simulacije. Pokušajte ponovo.");
      }
    } finally {
      setSimLoading(false);
    }
  }, [simMode.nSimulations, simMode.turnoutOverride]);

  const animateCounting = useCallback(() => {
    const cp = countingPathRef.current;
    if (!cp) return;
    if (simMode.stepIndex >= cp.steps - 1) {
      setSimMode(s => ({ ...s, running: false, progress: 1, stepIndex: cp.steps - 1 }));
      return;
    }

    const nextStep = simMode.stepIndex + 1;
    const progress = nextStep / (cp.steps - 1);
    
    setSimMode(s => ({ ...s, stepIndex: nextStep, progress }));
    
    if (cp.votes && simDataRef.current.length > 0) {
      const newData = simDataRef.current.map(p => {
        const votesArr = cp.votes[p.short_name];
        if (votesArr && votesArr[nextStep] !== undefined) {
          const currentVotes = votesArr[nextStep];
          const totalCounted = cp.counted_voters[nextStep];
          const currentPct = totalCounted > 0 ? (currentVotes / totalCounted) * 100 : 0;
          return { ...p, pct: currentPct, animatedVotes: currentVotes, animatedSeats: progress >= 1 ? p.seats : 0 };
        }
        return p;
      });
      simDataRef.current = newData;
      setSimData([...newData]); // trigger render
    }

    animationRef.current = requestAnimationFrame(() => {
      const delay = 100 / simMode.speed;
      setTimeout(() => animateCounting(), delay);
    });
  }, [simMode.stepIndex, simMode.speed]);

  const startAnimation = useCallback(() => {
    if (simMode.running) return;
    setSimMode(s => ({ ...s, running: true }));
    animateCounting();
  }, [animateCounting]);

  const pauseAnimation = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    setSimMode(s => ({ ...s, running: false }));
  }, []);

  const resetAnimation = useCallback(() => {
    pauseAnimation();
    setSimMode(s => ({ ...s, running: false, progress: 0, stepIndex: 0 }));
    if (countingPathRef.current) {
      setSimData(prev => prev.map(p => ({ ...p, pct: 0, animatedVotes: 0, animatedSeats: 0 })));
      simDataRef.current = simDataRef.current.map(p => ({ ...p, pct: 0, animatedVotes: 0, animatedSeats: 0 }));
    }
  }, [pauseAnimation]);

  const resetAll = useCallback(() => {
    pauseAnimation();
    if (abortRef.current) abortRef.current.abort();
    setSimMode({ electionId: null, running: false, progress: 0, stepIndex: 0, speed: 1, nSimulations: simMode.nSimulations, turnoutOverride: null });
    setSimData([]);
    simDataRef.current = [];
    setCountingPath(null);
    countingPathRef.current = null;
    setNationalData(null);
    setSimError(null);
  }, [pauseAnimation]);

  const startSim = useCallback((eid: number) => {
    if (simMode.running) return;
    resetAnimation();
    setSimMode({ electionId: eid, running: false, progress: 0, stepIndex: 0, speed: 1, nSimulations: simMode.nSimulations, turnoutOverride: simMode.turnoutOverride });
    fetchSimulationData(eid);
  }, [simMode.nSimulations, simMode.turnoutOverride, fetchSimulationData, resetAnimation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return (
    <>
      <main className="h-full w-full overflow-y-auto bg-[#0b0d12]">
        <div className="min-h-full w-full max-w-6xl mx-auto flex flex-col items-center justify-center px-5 py-8">
          <img src="/logo.svg" alt="Serbia Election Dashboard" width={44} height={44} className="mb-3" />
          <p className="text-[11px] uppercase tracking-[0.2em] text-white/35 font-medium mb-2">Serbia Elections</p>
          <h1 className="text-xl sm:text-2xl font-semibold text-white text-center">Koje izbore želite da vidite?</h1>
          <p className="text-sm text-white/40 mt-2 mb-6 text-center">Izaberite izborni ciklus za pregled rezultata po regionima i opštinama.</p>

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
                    onClick={() => { if (simMode.electionId) return; onPick(e.id); }}
                    className={`group text-left rounded-2xl bg-white/[0.04] border border-white/10 p-4 hover:bg-white/[0.07] hover:border-white/25 transition-all hover:-translate-y-0.5 h-full flex flex-col ${simMode.electionId === e.id ? "ring-2 ring-amber-500/50" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <StatusBadge status={e.status} />
                      <span className="text-white/25 group-hover:text-white/70 group-hover:translate-x-0.5 transition-all text-lg leading-none">→</span>
                    </div>
                    <p className="text-base font-semibold text-white leading-snug">{e.name}</p>
                    <p className="text-xs text-white/40 mt-1 tabular-nums">{formatDate(e.election_date)}</p>
                    <div className="flex items-center gap-4 mt-auto pt-3 border-t border-white/10">
                      <div>
                        <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">Vlast</p>
                        <p className="text-sm font-semibold text-white tabular-nums flex items-center gap-1.5 whitespace-nowrap">
                          {gov ? gov.map((p, i) => (
                            <span key={p} className="inline-flex items-center gap-1 shrink-0">
                              {i > 0 && <span className="text-white/30 font-normal">+</span>}
                              <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ background: PARTY_ABBR_COLORS[p] || "#888" }} />
                              <span>{p}</span>
                            </span>
                          )) : <span className="text-white/30">—</span>}
                        </p>
                      </div>
                      <div className="border-l border-white/10 pl-4">
                        <p className="text-[10px] uppercase tracking-wide text-white/35 leading-none mb-1">Ukupno glasova</p>
                        <p className="text-sm font-semibold text-white tabular-nums">{hasData ? Number(votes).toLocaleString("sr-RS") : "—"}</p>
                      </div>
                    </div>
                    <p className="text-[11px] text-white/30 mt-3 min-h-[16px]">
                      {!hasData ? (e.status === "upcoming" ? "Izbori predstoje." : "Još nema unetih rezultata.") : ""}
                    </p>
                    {e.status === "upcoming" && !simMode.electionId && (
                      <button type="button" onClick={(ev) => { ev.stopPropagation(); startSim(e.id); }}
                        className="mt-3 w-full px-3 py-2 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-medium hover:bg-amber-500/30 transition-colors flex items-center justify-center gap-2">
                        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M8 2a6 6 0 100 12A6 6 0 008 2z" strokeOpacity="0.5" />
                          <path d="M8 2a6 6 0 016 6" strokeLinecap="round" />
                        </svg>
                        Simulacija
                      </button>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {simMode.electionId && (
        <div className="fixed inset-0 z-50 bg-[#0b0d12]/95 backdrop-blur-sm flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#0e1117]">
            <button onClick={resetAll} className="p-2 rounded-lg bg-white/[0.04] border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-colors" title="Zatvori simulaciju">
              <svg className="w-5 h-5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12l5-5-5-5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <h2 className="text-lg font-semibold text-white truncate max-w-md mx-auto">{selectedElection?.name ?? "Simulacija"}</h2>
            <div className="flex items-center gap-2">
              <select value={simMode.nSimulations} onChange={(e) => setSimMode(s => ({ ...s, nSimulations: Number(e.target.value) }))} className="bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs text-white outline-none" title="Broj simulacija">
                <option value="200">200 (brzo)</option>
                <option value="500">500 (balans)</option>
                <option value="1000">1000 (precizno)</option>
                <option value="2000">2000 (najbolje)</option>
              </select>
              <select value={simMode.speed} onChange={(e) => setSimMode(s => ({ ...s, speed: Number(e.target.value) }))} className="bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs text-white outline-none" title="Brzina animacije">
                <option value="0.5">0.5x</option><option value="1">1x</option><option value="2">2x</option><option value="5">5x</option><option value="10">10x</option>
              </select>
              <select value={simMode.turnoutOverride ?? 62} onChange={(e) => setSimMode(s => ({ ...s, turnoutOverride: Number(e.target.value) }))} className="bg-white/[0.04] border border-white/10 rounded px-2 py-1 text-xs text-white outline-none" title="Izlaznost (prior mean za Monte Carlo)">
                <option value={50}>50%</option><option value={55}>55%</option><option value={60}>60%</option><option value={62}>62% (ankete)</option><option value={65}>65%</option><option value={70}>70%</option>
              </select>
              <button onClick={resetAnimation} className="px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/10 text-white/60 text-xs font-medium hover:bg-white/10 hover:text-white transition-colors">Reset</button>
            </div>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center p-6">
            {simError && (
              <div className="mb-6 p-4 rounded-lg bg-red-500/20 border border-red-500/30 text-red-300 text-sm text-center w-full max-w-2xl">
                {simError}
                <button onClick={() => fetchSimulationData(simMode.electionId!)} className="ml-4 underline hover:text-red-100">Pokušaj ponovo</button>
              </div>
            )}

            <div className="w-full max-w-4xl flex flex-col items-center gap-6">
              <div className="w-full max-w-2xl">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white">Progress brojanja</h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${simMode.running ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>
                    {simMode.running ? "U TOKU" : simMode.progress >= 1 ? "GOTOVO" : "PAUZA"}
                  </span>
                </div>
                <div className="flex items-center gap-2 mb-3">
                  <button onClick={simMode.running ? pauseAnimation : startAnimation} className="flex-1 px-3 py-2 rounded-lg bg-white/[0.06] border border-white/10 text-white text-xs font-medium hover:bg-white/10 transition-colors">
                    {simMode.running ? "Pauziraj" : "Pokreni"}
                  </button>
                  <button onClick={resetAnimation} className="px-3 py-2 rounded-lg bg-white/[0.06] border border-white/10 text-white/60 text-xs font-medium hover:bg-white/10 hover:text-white transition-colors">Reset</button>
                </div>
                <div className="mb-3"><label className="text-[10px] text-white/40 mb-1 block">Brzina: {simMode.speed}x</label>
                  <select value={simMode.speed} onChange={(e) => setSimMode(s => ({ ...s, speed: Number(e.target.value) }))} className="w-full bg-white/[0.08] border border-white/20 rounded px-2 py-1.5 text-xs text-white outline-none">
                    <option value="0.5">0.5x</option><option value="1">1x</option><option value="2">2x</option><option value="5">5x</option><option value="10">10x</option>
                  </select>
                </div>
                <div className="mb-3"><label className="text-[10px] text-white/40 mb-1 block">Izlaznost (prior): {simMode.turnoutOverride ?? 62}%</label>
                  <select value={simMode.turnoutOverride ?? 62} onChange={(e) => setSimMode(s => ({ ...s, turnoutOverride: Number(e.target.value) }))} className="w-full bg-white/[0.08] border border-white/20 rounded px-2 py-1.5 text-xs text-white outline-none">
                    <option value={50}>50%</option><option value={55}>55%</option><option value={60}>60%</option><option value={62}>62% (ankete)</option><option value={65}>65%</option><option value={70}>70%</option>
                  </select>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500 transition-all duration-300" style={{ width: `${simMode.progress * 100}%` }} />
                </div>
                <p className="text-right text-[10px] text-white/40 mt-1">{Math.round(simMode.progress * 100)}% gotovo</p>
                {nationalData && (
                  <div className="mt-3 p-3 bg-white/[0.03] border border-white/10 rounded-lg text-xs text-white/70">
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      <span title="Prosečna izlaznost iz Monte Carlo (95% CI)">Izlaznost: {nationalData.turnout_mean.toFixed(1)}% (95% CI: {nationalData.turnout_ci_lower.toFixed(1)}–{nationalData.turnout_ci_upper.toFixed(1)}%)</span>
                      <span title="Procenat nevažećih glasova">Nevažeći: {nationalData.invalid_pct_mean.toFixed(2)}%</span>
                      <span title="Verovatnoća apsolutne većine (≥126 mandata)">P(apsolutna većina): {(nationalData.p_sns_ge_126 * 100).toFixed(1)}%</span>
                      <span title="Verovatnoća da neka koalicija dobije većinu">P(većina): {(nationalData.p_sns_sps_ge_126 * 100).toFixed(1)}%</span>
                    </div>
                    <div className="text-[10px] text-white/50 border-t border-white/10 pt-2">Napomena: Izlaznost/nevažeći su iz anketi i tržišta. Korisnički unos menja prior mean.</div>
                  </div>
                )}
              </div>

              <div className="w-full max-w-2xl">
                {simLoading ? (
                  <div className="w-full max-w-2xl aspect-square bg-[#0b0d12] rounded-2xl border border-white/10 flex items-center justify-center">
                    <p className="text-white/30 text-center px-4">Učitavanje simulacije…</p>
                  </div>
                ) : simData.length > 0 ? (
                  <SimulationMandates parties={simData} totalSeats={250} threshold={3} animationProgress={simMode.progress} isRunning={simMode.running} />
                ) : (
                  <div className="w-full max-w-2xl aspect-square bg-[#0b0d12] rounded-2xl border border-white/10 flex items-center justify-center">
                    <p className="text-white/30 text-center px-4">Nema podataka za simulaciju</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}