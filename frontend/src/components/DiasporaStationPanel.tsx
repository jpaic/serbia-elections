"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import ResultBars from "./ResultBars";

export default function DiasporaStationPanel({
  electionId,
  rikStationId,
  city,
  country,
  placeName,
  pastTense = false,
  censusPct = 3,
  governingBallots = [],
  status = "live",
}: {
  electionId: number;
  rikStationId: number;
  city: string;
  country: string;
  placeName: string;
  pastTense?: boolean;
  censusPct?: number;
  governingBallots?: number[];
  status?: string;
}) {
  const { data, error, isLoading } = useSWR(
    ["station-by-rik", electionId, rikStationId],
    () => api.stationByRik(electionId, rikStationId),
    { refreshInterval: 30000 }
  );

  const loading = (isLoading || !data) && !error;
  return (
    <div className={`rounded-xl bg-white/[0.04] border border-white/10 p-4${loading ? " min-h-[360px]" : ""}`}>
      <p className="text-[11px] uppercase tracking-wide text-white/35 font-medium mb-1">
        Biračko mesto
      </p>
      <p className="text-sm font-semibold text-white leading-tight">
        {city} · {country}
      </p>
      <p className="text-xs text-white/50 mt-0.5 mb-3">{placeName}</p>
      {loading && (
        <div className="flex flex-col gap-2.5 animate-pulse" aria-label="Učitavanje rezultata">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full border-2 border-white/15 border-t-white/80 animate-spin" />
            <span className="text-xs text-white/50">Učitavanje rezultata…</span>
          </div>
          <div className="h-3 rounded bg-white/10 w-2/3 mt-1" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-1/2" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-3/5" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-2/3" />
          <div className="h-1.5 rounded-full bg-white/10" />
          <div className="h-3 rounded bg-white/10 w-1/3" />
          <div className="h-1.5 rounded-full bg-white/10" />
        </div>
      )}
      {error && (
        <p className="text-xs text-white/40">Za ovo biračko mesto trenutno nema dostupnih rezultata.</p>
      )}
      {data && data.results.length > 0 && (
        <ResultBars results={data.results} compact pastTense={pastTense} censusPct={censusPct} governingBallots={governingBallots} status={status} hideCensusText />
      )}
      {data && data.results.length === 0 && !error && (
        <p className="text-xs text-white/40">Za ovo biračko mesto trenutno nema dostupnih rezultata.</p>
      )}
    </div>
  );
}
