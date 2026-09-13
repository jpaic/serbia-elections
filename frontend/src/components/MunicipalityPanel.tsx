"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import ResultBars from "./ResultBars";

export default function MunicipalityPanel({
  electionId,
  municipalityId,
}: {
  electionId: number;
  municipalityId: number;
}) {
  const { data, error, isLoading } = useSWR(
    ["municipality-detail", electionId, municipalityId],
    () => api.municipalityDetail(electionId, municipalityId),
    { refreshInterval: 30000 }
  );

  return (
    <div style={{ background: "#F5F4EF", borderRadius: 8, padding: "1rem" }}>
      {isLoading && <p style={{ fontSize: 13, color: "#888" }}>Učitavanje…</p>}
      {error && <p style={{ fontSize: 13, color: "#791F1F" }}>Ne mogu da učitam detalje opštine.</p>}
      {data && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ fontSize: 16, fontWeight: 500 }}>{data.municipality.name}</span>
            <span style={{ fontSize: 13, color: "#666" }}>
              {data.municipality.registered_voters?.toLocaleString("sr-RS")} birača
            </span>
          </div>
          <ResultBars results={data.results} />
        </>
      )}
    </div>
  );
}
