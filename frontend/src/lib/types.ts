export interface Election {
  id: number;
  name: string;
  election_type: string;
  election_date: string;
  status: "upcoming" | "live" | "closed";
}

export interface PartyResult {
  id?: number;
  name: string;
  short_name: string;
  color_hex: string;
  votes: number;
  pct: number;
}

export interface ElectionSummary {
  election: Election;
  processed_pct: number;
  turnout_pct: number;
  results: PartyResult[];
}

export interface MunicipalityRow {
  id: number;
  name: string;
  region: string;
  total_stations: number;
  processed_stations: number;
  total_voted: number | null;
  registered_voters: number | null;
}

export interface MunicipalityDetail {
  municipality: {
    id: number;
    name: string;
    region: string;
    population: number;
    registered_voters: number;
  };
  results: PartyResult[];
}
