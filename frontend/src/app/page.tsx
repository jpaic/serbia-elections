"use client";

import { useState } from "react";
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

  const { data: municipalities, error: municipalitiesError } = useSWR(
    ["municipalities", ELECTION_ID],
    () => api.municipalities(ELECTION_ID),
    { refreshInterval: REFRESH_MS }
  );

  const error = summaryError || municipalitiesError;

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: 22, fontWeight: 500, marginBottom: 4 }}>
        {summary?.election.name || "Izbori"}
      </h1>

      {error && (
        <div
          style={{
            background: "#FCEBEB",
            color: "#791F1F",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 14,
          }}
        >
          Ne mogu da se povežem sa API-jem ({process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}).
          Proveri da li backend radi i da li je baza napunjena podacima.
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <MetricCard label="Obrađeno biračkih mesta" value={summary ? `${summary.processed_pct.toFixed(1)}%` : "—"} />
        <MetricCard label="Izlaznost" value={summary ? `${summary.turnout_pct.toFixed(1)}%` : "—"} />
        <MetricCard label="Status" value={summary ? statusLabel(summary.election.status) : "—"} />
      </div>

      <section style={{ marginBottom: 24 }}>
        {municipalities ? (
          <SerbiaMap
            municipalities={municipalities}
            selectedRegion={selectedRegion}
            onSelectRegion={(region) => {
              setSelectedRegion(region);
              setSelectedMunicipalityId(null);
            }}
          />
        ) : (
          <div style={{ padding: "4rem 0", textAlign: "center", color: "#888" }}>Učitavanje mape…</div>
        )}
      </section>

      {selectedRegion && municipalities && (
        <section style={{ marginBottom: 24 }}>
          <p style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>
            Opštine u regionu: {selectedRegion}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {municipalities
              .filter((m) => m.region === selectedRegion)
              .map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMunicipalityId(m.id)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: selectedMunicipalityId === m.id ? "2px solid #378ADD" : "1px solid #ddd",
                    background: "#fff",
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  {m.name} · {m.total_stations > 0 ? Math.round((100 * m.processed_stations) / m.total_stations) : 0}%
                </button>
              ))}
          </div>
        </section>
      )}

      {selectedMunicipalityId && (
        <section style={{ marginBottom: 24 }}>
          <MunicipalityPanel electionId={ELECTION_ID} municipalityId={selectedMunicipalityId} />
        </section>
      )}

      <section>
        <p style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>Ukupni rezultati</p>
        {summary ? <ResultBars results={summary.results} /> : null}
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#F5F4EF", borderRadius: 8, padding: "1rem" }}>
      <p style={{ fontSize: 13, color: "#666", margin: "0 0 4px" }}>{label}</p>
      <p style={{ fontSize: 24, fontWeight: 500, margin: 0 }}>{value}</p>
    </div>
  );
}

function statusLabel(status: string) {
  if (status === "live") return "Uživo";
  if (status === "closed") return "Završeno";
  return "Predstoji";
}
