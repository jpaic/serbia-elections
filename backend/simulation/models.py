"""Data models for election simulation."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class PartyData:
    """Core party information."""
    party_id: int
    short_name: str
    full_name: str
    color_hex: str
    is_minority: bool = False
    is_governing: bool = False


@dataclass
class PollData:
    """Polling data from a single pollster."""
    pollster: str
    date: datetime
    sample_size: int
    percentages: Dict[str, float]  # party short_name -> percentage
    source_url: str = ""
    weight: float = 1.0  # quality weight


@dataclass
class OddsData:
    """Betting odds from a bookmaker."""
    bookmaker: str
    date: datetime
    odds: Dict[str, float]  # party short_name -> decimal odds
    source_url: str = ""
    weight: float = 1.0


@dataclass
class PartyProjection:
    """Projected result for a single party."""
    party: "PartyData"
    vote_share_mean: float
    vote_share_std: float
    vote_share_ci_lower: float  # 95% CI lower
    vote_share_ci_upper: float  # 95% CI upper
    seats_mean: float
    seats_std: float
    seats_ci_lower: int  # 95% CI lower
    seats_ci_upper: int  # 95% CI upper
    seats_distribution: Dict[int, float]  # seats -> probability
    threshold_cleared_prob: float  # probability of crossing threshold


@dataclass
class SimulationResult:
    """Complete simulation result."""
    election_id: int
    simulation_date: datetime
    n_simulations: int
    parties: List["PartyProjection"]
    coalition_probs: Dict[str, float]  # coalition_name -> probability
    majority_prob: float  # probability of any coalition getting 126+ seats
    threshold: float
    total_seats: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class ElectionContext:
    """Context for simulation - polls, odds, parties."""
    election_id: int
    parties: List["PartyData"]
    polls: List["PollData"]
    odds: List["OddsData"]
    threshold: float
    total_seats: int = 250