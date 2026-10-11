import sys
import os
import psycopg2
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

# Get poll estimates
poll_estimates = engine._compute_poll_estimates(context)
filled = engine._fill_missing_parties(poll_estimates, context)
normalized = engine._normalize_estimates(filled)

with open('debug_votes_pct.txt', 'w', encoding='utf-8') as f:
    f.write("=== Normalized estimates ===\n")
    total_pct = 0
    for p in context.parties:
        val = normalized.get(p.short_name, 0)
        f.write(f"  BN={p.ballot_number:2d} | {p.short_name[:50]:50s} -> {val*100:.1f}%\n")
        total_pct += val * 100
    f.write(f"\nTotal: {total_pct:.1f}%\n")

    # Check what registered voters and turnout produce
    R = 6450523
    T = 0.62
    voted = int(R * T)
    inv_rate = 0.0235
    valid = int(voted * (1 - inv_rate))
    f.write(f"\nR={R}, T={T}, voted={voted}, invalid={voted-valid}, valid={valid}\n")
    
    # Calculate expected votes from percentages
    f.write("\n=== Expected votes from normalized pct ===\n")
    for p in context.parties:
        val = normalized.get(p.short_name, 0)
        expected_votes = val * valid
        f.write(f"  BN={p.ballot_number:2d} | {p.short_name[:40]:40s} -> pct={val*100:.1f}% votes={expected_votes:,.0f}\n")

    # Check counting_path
    # Run a quick simulation to see counting_path
    engine2 = ElectionSimulationEngine(n_simulations=1, turnout_prior_mean=62)
    results = engine2._run_monte_carlo_full(context, normalized)
    
    # Check counting_path from engine
    counting_path = engine._build_counting_path(results, context)
    
    f.write(f"\n=== Counting path check ===\n")
    f.write(f"Steps: {counting_path['steps']}\n")
    f.write(f"Counted voters at end: {counting_path['counted_voters'][-1]}\n")
    f.write(f"Total registered: {counting_path['total_registered']}\n")
    f.write(f"Final turnout: {counting_path['final_turnout']:.1f}%\n")
    f.write(f"Final invalid: {counting_path['final_invalid']:.2f}%\n")
    
    # Check votes at final step
    f.write(f"\n=== Final step votes vs valid ===\n")
    total_votes = 0
    for p_idx, short_name in enumerate(counting_path['votes'].keys()):
        votes = counting_path['votes'][short_name][-1]
        total_votes += votes
        f.write(f"  {short_name[:40]:40s} -> {votes}\n")
    f.write(f"Total votes in path: {total_votes}\n")
    f.write(f"Valid votes in rep sim: {results['valid_votes'][0]}\n")