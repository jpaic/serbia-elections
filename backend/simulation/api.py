"""Simulation API endpoints."""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from .engine import ElectionSimulationEngine
from .models import ElectionContext, PartyData, PollData, OddsData, SimulationResult
from db import get_db_connection

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class PollInput(BaseModel):
    pollster: str
    date: datetime
    sample_size: int
    percentages: Dict[str, float]
    source_url: str = ""
    weight: float = 1.0


class OddsInput(BaseModel):
    bookmaker: str
    date: datetime
    odds: Dict[str, float]
    source_url: str = ""
    weight: float = 1.0


class SimulationRequest(BaseModel):
    election_id: int
    n_simulations: int = 2000
    threshold: float = 3.0
    total_seats: int = 250
    turnout: int = 60
    polls: List[PollInput] = []
    odds: List[OddsInput] = []


class PartyProjectionResponse(BaseModel):
    short_name: str
    full_name: str
    color_hex: str
    ballot_number: Optional[int] = None
    vote_share_mean: float
    vote_share_ci_lower: float
    vote_share_ci_upper: float
    seats_mean: float
    seats_ci_lower: int
    seats_ci_upper: int
    seats_distribution: Dict[int, float]
    threshold_cleared_prob: float
    is_minority: bool
    is_governing: bool


class SimulationResponse(BaseModel):
    election_id: int
    simulation_date: datetime
    n_simulations: int
    parties: List[PartyProjectionResponse]
    coalition_probs: Dict[str, float]
    majority_prob: float
    threshold: float
    total_seats: int
    metadata: Dict


def get_party_data(election_id: int, conn) -> List[dict]:
    """Fetch party data from database."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, short_name, color_hex, is_minority, official_seats, ballot_number
               FROM parties WHERE election_id = %s ORDER BY ballot_number""",
            (election_id,)
        )
        rows = cur.fetchall()
        return [
            {
                "party_id": r[0],
                "short_name": r[2],
                "full_name": r[1],
                "color_hex": r[3],
                "is_minority": bool(r[4]),
                "is_governing": False,
                "ballot_number": r[6],
            }
            for r in rows
        ]


def get_latest_polls(election_id: int, conn) -> List[dict]:
    """Fetch latest polling data from database."""
    with conn.cursor() as cur:
        # Table polls now exists (created in schema migration)
        cur.execute("""
            SELECT pollster, published, sample_size, percentages, source_url, weight
            FROM polls 
            WHERE election_id = %s 
            ORDER BY published DESC 
            LIMIT 20
        """, (election_id,))
        rows = cur.fetchall()
        return [
            {
                "pollster": r[0], "date": r[1], "sample_size": r[2],
                "percentages": r[3], "source_url": r[4], "weight": r[5]
            }
            for r in rows
        ]


def get_latest_odds(election_id: int, conn) -> List[dict]:
    """Fetch latest betting odds from database (market_lines table)."""
    with conn.cursor() as cur:
        # market_lines has different structure - return empty for now
        # Odds are passed directly in request or handled separately
        return []


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    conn = Depends(get_db_connection)
):
    """Run Monte Carlo election simulation."""
    
    # Validate election exists
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM elections WHERE id = %s", (request.election_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Election not found")
    
    # Get party data
    parties = get_party_data(request.election_id, conn)
    if not parties:
        raise HTTPException(400, "No parties found for this election")
    
    # Get polls and odds (use provided or fetch from DB)
    polls = request.polls if request.polls else get_latest_polls(request.election_id, conn)
    odds = request.odds if request.odds else get_latest_odds(request.election_id, conn)
    
    # Build context - convert dicts to dataclasses
    context = ElectionContext(
        election_id=request.election_id,
        parties=[PartyData(
            party_id=p["party_id"], short_name=p["short_name"],
            full_name=p["full_name"], color_hex=p["color_hex"],
            is_minority=p["is_minority"], is_governing=p["is_governing"],
            ballot_number=p["ballot_number"]
        ) for p in parties],
        polls=[PollData(**p) if isinstance(p, dict) else p for p in polls],
        odds=[OddsData(**o) for o in odds],
        threshold=request.threshold,
        total_seats=request.total_seats
    )
    
    # Run simulation
    engine = ElectionSimulationEngine(
        n_simulations=request.n_simulations,
        threshold=request.threshold,
        total_seats=request.total_seats,
        turnout=request.turnout
    )
    
    result = engine.run_simulation(ElectionContext(
        election_id=context.election_id,
        parties=context.parties,
        polls=context.polls,
        odds=context.odds,
        threshold=context.threshold,
        total_seats=context.total_seats
    ))
    
    # Convert to response format
    party_responses = []
    for proj in result.parties:
        party_responses.append(PartyProjectionResponse(
            short_name=proj.party.short_name,
            full_name=proj.party.full_name,
            color_hex=proj.party.color_hex,
            ballot_number=proj.party.ballot_number,
            vote_share_mean=proj.vote_share_mean,
            vote_share_ci_lower=proj.vote_share_ci_lower,
            vote_share_ci_upper=proj.vote_share_ci_upper,
            seats_mean=proj.seats_mean,
            seats_ci_lower=proj.seats_ci_lower,
            seats_ci_upper=proj.seats_ci_upper,
            seats_distribution=proj.seats_distribution,
            threshold_cleared_prob=proj.threshold_cleared_prob,
            is_minority=proj.party.is_minority,
            is_governing=proj.party.is_governing
        ))
    
    return SimulationResponse(
        election_id=result.election_id,
        simulation_date=result.simulation_date,
        n_simulations=result.n_simulations,
        parties=party_responses,
        coalition_probs=result.coalition_probs,
        majority_prob=result.majority_prob,
        threshold=result.threshold,
        total_seats=result.total_seats,
        metadata=result.metadata
    )


@router.get("/status/{election_id}")
async def simulation_status(election_id: int, conn = Depends(get_db_connection)):
    """Get simulation status/cached results."""
    # In production, check for cached results
    return {"election_id": election_id, "status": "ready"}


@router.get("/parties/{election_id}")
async def get_simulation_parties(election_id: int, conn = Depends(get_db_connection)):
    """Get parties available for simulation."""
    parties = get_party_data(election_id, conn)
    return [
        {
            "party_id": p["party_id"],
            "short_name": p["short_name"],
            "full_name": p["full_name"],
            "color_hex": p["color_hex"],
            "is_minority": p["is_minority"],
            "is_governing": p["is_governing"]
        }
        for p in parties
    ]