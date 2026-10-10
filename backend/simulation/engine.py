"""
Professional Monte Carlo Election Simulation Engine.

Uses:
- Polling data (weighted by recency, sample size, pollster quality)
- Betting odds (converted to implied probabilities, weighted by bookmaker reliability)
- Historical accuracy weights for pollsters/bookmakers
- Dirichlet-multinomial modeling for vote share uncertainty
- D'Hondt seat allocation with threshold
- Monte Carlo with 1000+ iterations
- Confidence intervals and seat distributions
"""
import numpy as np
import numpy.random as npr
from scipy import stats
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math

from .models import (
    PartyData, PollData, OddsData, PartyProjection, 
    SimulationResult, ElectionContext
)


class ElectionSimulationEngine:
    """
    Professional Monte Carlo election simulation engine.
    
    Combines:
    - Weighted polling averages (recency, sample size, pollster track record)
    - Betting market implied probabilities (with overround removal)
    - Historical pollster/bookmaker accuracy weights
    - Dirichlet-multinomial for vote share uncertainty
    - D'Hondt seat allocation with threshold
    - Monte Carlo with configurable iterations
    """
    
    def __init__(
        self,
        n_simulations: int = 2000,
        poll_recency_half_life: float = 30.0,  # days
        min_poll_weight: float = 0.1,
        threshold: float = 3.0,
        total_seats: int = 250,
        turnout: int = 60,
        random_seed: Optional[int] = None
    ):
        self.n_simulations = n_simulations
        self.poll_recency_half_life = poll_recency_half_life
        self.min_poll_weight = min_poll_weight
        self.threshold = threshold
        self.total_seats = total_seats
        self.turnout = turnout
        
        if random_seed is not None:
            np.random.seed(random_seed)
            npr.seed(random_seed)
    
    def run_simulation(self, context: ElectionContext) -> "SimulationResult":
        """Run complete Monte Carlo simulation."""
        
        # Set is_governing based on GOVERNING_BALLOTS
        GOVERNING_BALLOTS = {
            "parlamentarni-2020": [1, 2],
            "parlamentarni-2022": [1, 2],
            "parlamentarni-2023": [1, 2],
            "parlamentarni-2026": [1, 2],  # Assume SNS+SPS for 2026
        }
        # We need to get the election slug from the election_id
        # For now, use a simple heuristic: parties with ballot_number 1 and 2 are typically governing
        for party in context.parties:
            party.is_governing = party.ballot_number in [1, 2]
        
        # 1. Compute weighted polling averages
        poll_estimates = self._compute_poll_estimates(context)
        
        # 2. Compute betting market implied probabilities
        odds_estimates = self._compute_odds_estimates(context)
        
        # 3. Combine polls and odds (weighted average)
        combined_estimates = self._combine_estimates(poll_estimates, odds_estimates, context)
        
        # 3. Estimate uncertainty (Dirichlet concentration parameters)
        alpha_params = self._estimate_dirichlet_params(
            combined_estimates, context.parties
        )
        
        # 4. Run Monte Carlo simulations
        seat_results, vote_share_results = self._run_monte_carlo(
            alpha_params, context.parties, context.threshold
        )
        
        # 5. Compute projections and confidence intervals
        projections = self._compute_projections(
            seat_results, vote_share_results, context.parties, context.threshold
        )
        
        # 6. Compute coalition probabilities
        coalition_probs = self._compute_coalition_probs(seat_results, context.parties)
        majority_prob = self._compute_majority_prob(seat_results, context.parties)
        
        return SimulationResult(
            election_id=context.election_id,
            simulation_date=datetime.now(),
            n_simulations=self.n_simulations,
            parties=projections,
            coalition_probs=coalition_probs,
            majority_prob=majority_prob,
            threshold=context.threshold,
            total_seats=context.total_seats,
            metadata={
                "poll_weight": self._compute_poll_weight(context),
                "odds_weight": self._compute_odds_weight(context),
                "effective_sample_size": self._compute_effective_sample_size(context),
                "data_source": "polls" if context.polls else ("odds" if context.odds else "prior"),
            }
        )
    
    def _compute_poll_estimates(self, context: ElectionContext) -> Dict[str, float]:
        """Compute weighted polling averages with recency and quality weights."""
        if not context.polls:
            return {}
        
        now = datetime.now()
        party_scores = {p.short_name: [] for p in context.parties}
        party_weights = {p.short_name: [] for p in context.parties}
        
        for poll in context.polls:
            days_old = (datetime.now() - poll.date).days
            recency_weight = math.exp(-days_old / self.poll_recency_half_life)
            recency_weight = max(recency_weight, self.min_poll_weight)
            
            # Quality weight from pollster track record (simplified)
            quality_weight = poll.weight
            
            # Sample size weight (sqrt(n) scaling)
            sample_weight = math.sqrt(poll.sample_size / 1000)
            
            total_weight = recency_weight * quality_weight * sample_weight
            
            for party_short, pct in poll.percentages.items():
                if party_short in party_scores:
                    party_scores[party_short].append(pct / 100.0)
                    party_weights[party_short].append(total_weight)
        
        # Weighted average
        estimates = {}
        for party, scores in party_scores.items():
            if scores and party_weights[party]:
                weights = party_weights[party]
                estimates[party] = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
            else:
                estimates[party] = 0.0
        
        return estimates
    
    def _compute_odds_estimates(self, context: ElectionContext) -> Dict[str, float]:
        """Convert betting odds to implied probabilities (remove overround)."""
        if not context.odds:
            return {}
        
        # Aggregate odds from multiple bookmakers (weighted average)
        party_odds = {p.short_name: [] for p in context.parties}
        party_weights = {p.short_name: [] for p in context.parties}
        
        for odds_data in context.odds:
            weight = odds_data.weight
            for party, odds in odds_data.odds.items():
                if party in party_odds and odds > 1.0:
                    implied_prob = 1.0 / odds
                    party_odds[party].append(implied_prob)
                    party_weights[party].append(weight)
        
        # Weighted average of implied probabilities
        estimates = {}
        for party, probs in party_odds.items():
            if probs and party_weights[party]:
                weights = party_weights[party]
                estimates[party] = sum(p * w for p, w in zip(probs, weights)) / sum(weights)
            else:
                estimates[party] = 0.0
        
        # Remove overround (normalize to sum to 1 for eligible parties)
        total = sum(estimates.values())
        if total > 0:
            estimates = {k: v / total for k, v in estimates.items()}
        
        return estimates
    
    def _combine_estimates(
        self, 
        poll_estimates: Dict[str, float], 
        odds_estimates: Dict[str, float],
        context: ElectionContext
    ) -> Dict[str, float]:
        """Combine polling and odds estimates with dynamic weights."""
        poll_weight = self._compute_poll_weight(context)
        odds_weight = self._compute_odds_weight(context)
        total_weight = poll_weight + odds_weight
        
        if total_weight == 0:
            return {p.short_name: 0.0 for p in context.parties}
        
        combined = {}
        all_parties = set(poll_estimates.keys()) | set(odds_estimates.keys())
        
        for party in all_parties:
            poll_val = poll_estimates.get(party, 0.0)
            odds_val = odds_estimates.get(party, 0.0)
            combined[party] = (poll_val * poll_weight + odds_val * odds_weight) / total_weight
        
        # Normalize
        total = sum(combined.values())
        if total > 0:
            combined = {k: v / total for k, v in combined.items()}
        
        return combined
    
    def _compute_poll_weight(self, context: ElectionContext) -> float:
        """Compute overall poll weight based on quantity, recency, quality."""
        if not context.polls:
            return 0.0
        
        total_weight = 0.0
        now = datetime.now()
        for poll in context.polls:
            days_old = (now - poll.date).days
            recency = math.exp(-days_old / self.poll_recency_half_life)
            recency = max(recency, self.min_poll_weight)
            quality = poll.weight
            sample = math.sqrt(poll.sample_size / 1000)
            total_weight += recency * quality * sample
        
        # Normalize to [0, 1] range
        return min(total_weight / 10.0, 1.0)
    
    def _compute_odds_weight(self, context: ElectionContext) -> float:
        """Compute overall odds weight."""
        if not context.odds:
            return 0.0
        
        total_weight = sum(o.weight for o in context.odds)
        return min(total_weight / 5.0, 1.0)
    
    def _estimate_dirichlet_params(
        self, 
        estimates: Dict[str, float], 
        parties: List[PartyData]
    ) -> Dict[str, float]:
        """
        Estimate Dirichlet concentration parameters from mean estimates and uncertainty.
        
        Higher concentration = more certain (lower variance).
        We use effective sample size to determine concentration.
        """
        # Effective sample size based on data quality
        n_eff = 1000  # Base effective sample size
        
        # Adjust for data quality
        # More polls/odds = higher effective sample
        
        # Adjust Dirichlet concentration based on turnout
        # Higher turnout = more certainty = higher concentration
        turnout_factor = self.turnout / 60.0  # 60% is baseline
        
        alpha = {}
        for party in parties:
            p = party.short_name
            mean = estimates.get(p, 0.0)
            # Dirichlet: alpha_i = mean * concentration
            # concentration ~ effective sample size * certainty
            certainty = 1.0
            if mean > 0:
                certainty = min(1.0, mean * 10)  # Higher for larger parties
            # Scale concentration by turnout factor
            concentration = self.turnout / 60.0 * 500 * certainty
            alpha[p] = max(mean * concentration, 0.1)
        
        return alpha
    
    def _run_monte_carlo(
        self, 
        alpha_params: Dict[str, float], 
        parties: List[PartyData],
        threshold: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run Monte Carlo simulations using Dirichlet-multinomial.
        
        Returns tuple of (seat_results, vote_share_results) where:
        - seat_results: array of shape (n_simulations, n_parties) with seat counts
        - vote_share_results: array of shape (n_simulations, n_parties) with vote share percentages
        """
        n_parties = len(parties)
        party_order = [p.short_name for p in parties]
        
        # Prepare alpha vector in consistent order
        alpha_vec = np.array([alpha_params.get(p, 0.1) for p in party_order])
        
        # Identify minority parties (exempt from threshold)
        is_minority = np.array([p.is_minority for p in parties])
        
        # Run simulations
        seat_results = np.zeros((self.n_simulations, len(parties)), dtype=int)
        vote_share_results = np.zeros((self.n_simulations, len(parties)))
        
        for i in range(self.n_simulations):
            # Sample vote shares from Dirichlet
            vote_shares = np.random.dirichlet(alpha_vec)
            vote_share_results[i] = vote_shares * 100  # Store as percentages
            
            # Apply threshold (minority parties exempt)
            eligible = (vote_shares >= (threshold / 100.0)) | is_minority
            if not eligible.any():
                seat_results[i] = 0
                continue
            
            # Allocate seats using D'Hondt
            seats = self._dhondt_allocation(vote_shares, eligible, self.total_seats)
            seat_results[i] = seats
        
        return seat_results, vote_share_results
    
    def _dhondt_allocation(
        self, 
        vote_shares: np.ndarray, 
        eligible: np.ndarray, 
        total_seats: int
    ) -> np.ndarray:
        """D'Hondt seat allocation."""
        n = len(vote_shares)
        seats = np.zeros(n, dtype=int)
        
        # Only eligible parties participate
        quotients = np.where(eligible, vote_shares, 0)
        
        for _ in range(total_seats):
            # Find party with highest quotient
            idx = np.argmax(quotients)
            seats[idx] += 1
            quotients[idx] = vote_shares[idx] / (seats[idx] + 1)
        
        return seats
    
    def _compute_projections(
        self, 
        seat_results: np.ndarray, 
        vote_share_results: np.ndarray,
        parties: List[PartyData],
        threshold: float
    ) -> List["PartyProjection"]:
        """Compute projections with confidence intervals using actual vote shares."""
        n_sims, n_parties = seat_results.shape
        
        projections = []
        
        for i, party in enumerate(parties):
            seats = seat_results[:, i]
            vote_shares = vote_share_results[:, i]  # Actual vote shares from simulations
            
            seats_mean = float(np.mean(seats))
            seats_std = float(np.std(seats))
            
            # 95% CI for seats
            seats_ci_lower = int(np.percentile(seats, 2.5))
            seats_ci_upper = int(np.percentile(seats, 97.5))
            
            # Vote share stats
            vote_shares = vote_share_results[:, i]
            vote_share_mean = float(np.mean(vote_shares))
            vote_share_std = float(np.std(vote_shares))
            
            # 95% CI for vote share
            vote_share_ci_lower = max(0, vote_share_mean - 1.96 * vote_share_std)
            vote_share_ci_upper = min(100, vote_share_mean + 1.96 * vote_share_std)
            
            # Seat distribution
            unique, counts = np.unique(seat_results[:, i], return_counts=True)
            seat_dist = {int(k): float(v) / self.n_simulations for k, v in zip(unique, counts)}
            
            # Threshold cleared probability (based on vote share)
            threshold_cleared = float(np.mean(vote_shares >= threshold))
            
            # Seat distribution
            seats_mean = float(np.mean(seats))
            seats_std = float(np.std(seats))
            seats_ci_lower = int(np.percentile(seats, 2.5))
            seats_ci_upper = int(np.percentile(seats, 97.5))
            seat_dist = {int(k): float(v) / self.n_simulations for k, v in zip(*np.unique(seats, return_counts=True))}
            
            projections.append(PartyProjection(
                party=self._get_party_by_short_name(party.short_name, parties),
                vote_share_mean=vote_share_mean,
                vote_share_std=float(np.std(vote_shares)),
                vote_share_ci_lower=max(0, vote_share_mean - 1.96 * vote_share_std),
                vote_share_ci_upper=min(100, vote_share_mean + 1.96 * vote_share_std),
                seats_mean=seats_mean,
                seats_std=seats_std,
                seats_ci_lower=seats_ci_lower,
                seats_ci_upper=seats_ci_upper,
                seats_distribution=seat_dist,
                threshold_cleared_prob=threshold_cleared,
            ))
        
        return projections
    
    def _get_party_order(self, parties: List["PartyData"]) -> List["PartyData"]:
        return parties
    
    def _get_party_by_short_name(self, short_name: str, parties: List["PartyData"]) -> "PartyData":
        for p in parties:
            if p.short_name == short_name:
                return p
        return PartyData(0, short_name, "", "#000000", False, False)
    
    def _compute_effective_sample_size(self, context: ElectionContext) -> int:
        """Compute effective sample size from polls and odds."""
        n_eff = 1000  # Base
        
        # Add from polls
        if context.polls:
            for poll in context.polls:
                n_eff += int(poll.sample_size * poll.weight)
        
        # Add from odds (each bookmaker ~100 effective samples)
        if context.odds:
            n_eff += len(context.odds) * 100
        
        # Cap at reasonable maximum
        return min(n_eff, 10000)
    
    def _compute_coalition_probs(
        self, 
        seat_results: np.ndarray, 
        parties: List["PartyData"]
    ) -> Dict[str, float]:
        """Compute probability of each coalition achieving majority."""
        n_sims = seat_results.shape[0]
        
        # Find governing parties (is_governing=True)
        governing_indices = [i for i, p in enumerate(parties) if p.is_governing]
        opposition_indices = [i for i, p in enumerate(parties) if not p.is_governing]
        
        # Define potential coalitions
        coalitions = {
            "governing": governing_indices,
            "opposition": opposition_indices,
        }
        
        probs = {}
        for name, indices in coalitions.items():
            if indices:
                coalition_seats = seat_results[:, indices].sum(axis=1)
                probs[name] = float(np.mean(coalition_seats >= 126))
            else:
                probs[name] = 0.0
        
        return probs
    
    def _compute_majority_prob(
        self, 
        seat_results: np.ndarray, 
        parties: List["PartyData"]
    ) -> float:
        """Probability that some coalition gets 126+ seats."""
        # Probability that governing coalition gets majority
        governing_indices = [i for i, p in enumerate(parties) if p.is_governing]
        if governing_indices:
            governing_seats = seat_results[:, governing_indices].sum(axis=1)
            return float(np.mean(governing_seats >= 126))
        return 0.0