import sys
import os
import psycopg2
import numpy as np
sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")

from dotenv import load_dotenv
load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

cur.execute("SELECT id, name, short_name, color_hex, is_minority, official_seats, ballot_number FROM parties WHERE election_id = 3 ORDER BY ballot_number")
rows = cur.fetchall()
parties = [
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

cur.execute("SELECT pollster, published, sample_size, percentages, source_url, weight FROM polls WHERE election_id = 3 ORDER BY published DESC LIMIT 20")
rows = cur.fetchall()
polls = [
    {
        "pollster": r[0], "date": r[1], "sample_size": r[2],
        "percentages": r[3], "source_url": r[4], "weight": r[5]
    }
    for r in rows
]

cur.close()
c.close()

sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")
from simulation.engine import ElectionSimulationEngine
from simulation.models import ElectionContext, PartyData, PollData
import numpy as np

engine = ElectionSimulationEngine(n_simulations=100, turnout_prior_mean=62)

context = ElectionContext(
    election_id=3,
    parties=[PartyData(
        party_id=p["party_id"], short_name=p["short_name"],
        full_name=p["full_name"], color_hex=p["color_hex"],
        is_minority=p["is_minority"], is_governing=p["is_governing"],
        ballot_number=p["ballot_number"]
    ) for p in parties],
    polls=[PollData(**p) for p in polls],
    odds=[],
    threshold=3.0,
    total_seats=250,
    registered_voters=6450523
)

# Get mean shares
poll_estimates = engine._compute_poll_estimates(context)
filled = engine._fill_missing_parties(poll_estimates, context)
normalized = engine._normalize_estimates(filled)

party_order = [p.short_name for p in context.parties]
mean_shares = np.array([normalized.get(p, 0.0) for p in party_order])

with open('debug_mean_shares.txt', 'w', encoding='utf-8') as f:
    f.write('Mean shares:\n')
    for p, v in zip(party_order, mean_shares):
        f.write(f'  {p[:50]:50s} -> {v*100:.1f}%\n')
    f.write(f'\nSum: {np.sum(mean_shares):.4f}\n')

    # Check counting_path
    poll_estimates = engine._compute_poll_estimates(context)
    filled = engine._fill_missing_parties(poll_estimates, context)
    normalized = engine._normalize_estimates(filled)
    
    engine2 = ElectionSimulationEngine(n_simulations=100, turnout_prior_mean=62)
    context2 = ElectionContext(
        election_id=3,
        parties=[PartyData(
            party_id=p["party_id"], short_name=p["short_name"],
            full_name=p["full_name"], color_hex=p["color_hex"],
            is_minority=p["is_minority"], is_governing=p["is_governing"],
            ballot_number=p["ballot_number"]
        ) for p in parties],
        polls=[PollData(**p) for p in polls],
        odds=[],
        threshold=3.0,
        total_seats=250,
        registered_voters=6450523
    )
    
    results = engine2._run_monte_carlo_full(context2, normalized)
    counting_path = engine2._build_counting_path(results, context2)
    
    with open('debug_cp2.txt', 'w', encoding='utf-8') as f:
        f.write(f"Counting path steps: {counting_path['steps']}\n")
        f.write(f"Counted voters at end: {counting_path['counted_voters'][-1]}\n")
        f.write(f"Total registered: {counting_path['total_registered']}\n")
        f.write(f"Final turnout: {counting_path['final_turnout']:.1f}%\n")
        f.write(f"Final invalid: {counting_path['final_invalid']:.2f}%\n")
        f.write(f"\n=== Final step votes ===\n")
        total_votes = 0
        for p_idx, short_name in enumerate(counting_path['votes'].keys()):
            votes = counting_path['votes'][short_name][-1]
            total_votes += votes
            f.write(f"  {short_name[:40]:40s} -> {votes}\n")
        f.write(f"Total votes in path: {total_votes}\n")
        f.write(f"Valid votes expected: ~3905339\n")