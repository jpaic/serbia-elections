export interface Election {
  id: number;
  slug: string | null;
  stations_with_results: number;
  total_votes: number;
  municipalities_with_data: number;
  name: string;
  election_type: string;
  election_date: string;
  status: "upcoming" | "live" | "closed";
  prime_minister?: string | null;
  pm_party?: string | null;
  prime_ministers?: { name: string; party?: string | null; period?: string | null }[] | null;
}

export interface PartyResult {
  id?: number;
  name: string;
  short_name: string;
  color_hex: string;
  ballot_number?: number | null;
  is_minority?: boolean | null;
  votes: number;
  pct: number;
}

export interface PartyData {
  short_name: string;
  color_hex: string;
  pct: number;
  votes_mean?: number;
  seats: number;
  is_governing: boolean;
  ballot_number: number | null;
  is_minority: boolean;
  animatedSeats?: number;
  animatedVotes?: number;
  animatedPct?: number;
}

export interface SummaryParty {
  ballot_number: number | null;
  name: string;
  short_name: string;
  color_hex: string | null;
  is_minority: boolean;
}

export interface ElectionSummary {
  election: Election;
  processed_pct: number;
  turnout_pct: number;
  total_stations: number;
  total_voted: number;
  total_registered: number;
  parties: SummaryParty[];
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
  parent_name?: string | null;
}

export interface MandateParty extends PartyResult {
  ballot_number: number;
  is_minority: boolean;
  seats: number;
}

export interface MandatesResponse {
  total_seats: number;
  threshold_pct: number;
  valid_votes: number;
  official: boolean;
  parties: MandateParty[];
}

export interface SwingInfo {
  change_pp: number | null;
  prev_party: string | null;
  prev_pct: number | null;
}

export interface SwingNode {
  municipality_id?: number;
  region?: string;
  change_pp: number | null;
  prev_party: string | null;
  prev_pct: number | null;
}

export interface SwingResponse {
  prev_election: { id: number; slug: string; name: string; election_date: string } | null;
  municipalities: SwingNode[];
  regions: SwingNode[];
}

export interface DiasporaStationResult {
  rik_station_id: number;
  short_name: string;
  name: string;
  color_hex: string | null;
  votes: number;
  pct: number;
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
  parent_name?: string | null;
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

export interface PartyProjection {
  party: PartyData;
  ballot_number: number | null;
  vote_share_mean: number;
  vote_share_std: number;
  vote_share_ci_lower: number;
  vote_share_ci_upper: number;
  votes_mean: number;
  votes_ci_lower: number;
  votes_ci_upper: number;
  seats_mean: number;
  seats_std: number;
  seats_ci_lower: number;
  seats_ci_upper: number;
  seats_distribution: Record<number, number>;
  threshold_cleared_prob: number;
}

export interface CountingPath {
  steps: number;
  counted_voters: number[];
  votes: Record<string, number[]>;
  total_registered: number;
  final_turnout: number;
  final_invalid: number;
}

export interface NationalAggregates {
  registered_voters: number;
  turnout_mean: number;
  turnout_ci_lower: number;
  turnout_ci_upper: number;
  invalid_pct_mean: number;
  p_sns_ge_126: number;
  p_sns_sps_ge_126: number;
  p_studentska_largest: number;
  p_hung_parliament: number;
}

export interface SimulationResponse {
  election_id: number;
  simulation_date: string;
  n_simulations: number;
  parties: PartyProjection[];
  coalition_probs: Record<string, number>;
  majority_prob: number;
  threshold: number;
  total_seats: number;
  metadata: {
    poll_weight: number;
    market_weight: number;
    effective_sample_size: number;
    data_source: string;
    governing_assumption: string;
    registered_voters: number;
    turnout_prior_mean: number;
    turnout_prior_sd: number;
    invalid_ballots_mean: number;
    swing_sd: number;
    minority_coeff: number;
    counting_path: CountingPath;
    national: NationalAggregates;
  };
}
