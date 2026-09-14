export interface Election {
  id: number;
  slug: string | null;
  stations_with_results: number;
  total_votes: number;
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
  rzs_code?: string | null;
  total_stations: number;
  processed_stations: number;
  processed_pct: number;
  turnout_pct: number;
  total_voted: number | null;
  registered_voters: number | null;
  leader: PartyResult | null;
  margin_pct: number;
  results: PartyResult[];
}

export interface StationDetail {
  station: {
    id: number;
    name: string;
    municipality_id: number;
    registered_voters: number | null;
  };
  results: PartyResult[];
  live: boolean;
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

export interface RegionResult {
  region: string;
  total_stations: number;
  processed_stations: number;
  processed_pct: number;
  turnout_pct: number;
  total_voted: number | null;
  registered_voters: number | null;
  leader: PartyResult | null;
  margin_pct: number;
  results: PartyResult[];
}
