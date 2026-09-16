"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import ResultBars from "./ResultBars";

export default function MunicipalityPanel({
  electionId,
  municipalityId,
  pastTense = false,
  censusPct = 3,
  governingBallots = [],
  status = "live",
}: {
  electionId: number;
  municipalityId: number;
  pastTense?: boolean;
  censusPct?: number;
  governingBallots?: number[];
  status?: string;
}) {
  const { data, error, isLoading } = useSWR(
    ["municipality-detail", electionId, municipalityId],
    () => api.municipalityDetail(electionId, municipalityId),
    { refreshInterval: 30000 }
  );

  const loading = (isLoading || !data) && !error;
  return (
    <div className={`rounded-xl bg-white/[0.04] border border-white/10 p-4${loading ? " min-h-[460px]" : ""}`}>
      {loading && (
        <div className="flex flex-col gap-2.5 animate-pulse" aria-label="Učitavanje rezultata opštine">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full border-2 border-white/15 border-t-white/80 animate-spin" />
            <span className="text-xs text-white/50">Učitavanje rezultata opštine…</span>
          </div>
          <div className="h-3 rounded bg-white/10 w-2/3 mt-1" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-1/2" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-3/5" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-2/3" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-1/2" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-3/5" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-1/3" />
          <div className="h-1.5 rounded-full bg-white/10" />
        </div>
      )}
      {error && <p className="text-xs text-red-400">Ne mogu da učitam detalje opštine.</p>}
      {data && (
        <>
          <div className="flex items-start justify-between mb-3 gap-2">
            <span className="text-base font-semibold text-white leading-tight">
              {data.municipality.name}
              {data.parent_name && (
                <span className="block text-[11px] font-normal text-white/40 mt-0.5">
                  Deo opštine {data.parent_name} — prikazani matični rezultati iz vremena pre osamostaljenja
                </span>
              )}
            </span>
            <span className="text-[11px] text-white/40 tabular-nums shrink-0 pt-0.5">
              {data.municipality.registered_voters?.toLocaleString("sr-RS")} birača
            </span>
          </div>
          <ResultBars results={data.results} pastTense={pastTense} censusPct={censusPct} governingBallots={governingBallots} status={status} hideCensusText />
        </>
      )}
    </div>
  );
}
