const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    throw new Error(`Zahtev ka ${path} nije uspeo (${res.status})`);
  }
  return res.json();
}

export const api = {
  elections: () => getJson<import("./types").Election[]>("/elections"),
  summary: (electionId: number) =>
    getJson<import("./types").ElectionSummary>(`/elections/${electionId}/summary`),
  municipalities: (electionId: number) =>
    getJson<import("./types").MunicipalityRow[]>(`/elections/${electionId}/municipalities`),
  regions: (electionId: number) =>
    getJson<import("./types").RegionResult[]>(`/elections/${electionId}/regions`),
  municipalityDetail: (electionId: number, municipalityId: number) =>
    getJson<import("./types").MunicipalityDetail>(
      `/elections/${electionId}/municipalities/${municipalityId}`
    ),
  stationByRik: (electionId: number, rikStationId: number) =>
    getJson<import("./types").StationDetail>(
      `/elections/${electionId}/stations/by-rik/${rikStationId}`
    ),
  mandates: (electionId: number) =>
    getJson<import("./types").MandatesResponse>(
      `/elections/${electionId}/mandates`
    ),
  diaspora: (electionId: number) =>
    getJson<import("./types").DiasporaStationResult[]>(
      `/elections/${electionId}/diaspora`
    ),
  swing: (electionId: number) =>
    getJson<import("./types").SwingResponse>(
      `/elections/${electionId}/swing`
    ),
  simulation: {
    run: (body: {
      election_id: number;
      n_simulations: number;
      threshold: number;
      total_seats: number;
      polls: any[];
      odds: any[];
    }) =>
      getJson<import("./types").SimulationResponse>(`/api/simulation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  },
};
