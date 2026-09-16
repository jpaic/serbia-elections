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
}: {
  electionId: number;
  municipalityId: number;
  pastTense?: boolean;
  censusPct?: number;
  governingBallots?: number[];
}) {
  const { data, error, isLoading } = useSWR(
    ["municipality-detail", electionId, municipalityId],
    () => api.municipalityDetail(electionId, municipalityId),
    { refreshInterval: 30000 }
  );

  return (
    <div className="rounded-xl bg-white/[0.04] border border-white/10 p-4">
      {isLoading && <p className="text-xs text-white/40">Učitavanje…</p>}
      {error && <p className="text-xs text-red-400">Ne mogu da učitam detalje opštine.</p>}
      {data && (
        <>
          <div className="flex items-start justify-between mb-3 gap-2">
            <span className="text-base font-semibold text-white leading-tight">
              {data.municipality.name}
            </span>
            <span className="text-[11px] text-white/40 tabular-nums shrink-0 pt-0.5">
              {data.municipality.registered_voters?.toLocaleString("sr-RS")} birača
            </span>
          </div>
          <ResultBars results={data.results} pastTense={pastTense} censusPct={censusPct} governingBallots={governingBallots} />
        </>
      )}
    </div>
  );
}
