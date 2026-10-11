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

# Monkey-patch _run_monte_carlo_full to debug
engine = ElectionSimulationEngine(n_simulations=100, turnout_prior_mean=62)

original_mc = engine._run_monte_carlo_full

def debug_mc(context, estimates):
    import numpy as np
    with open('debug_engine_mc.txt', 'w', encoding='utf-8') as f:
        f.write("=== _run_monte_carlo_full debug ===\n")
        n_parties = len(context.parties)
        party_order = [p.short_name for p in context.parties]
        is_minority_arr = np.array([p.is_minority for p in context.parties])
        
        mean_shares = np.array([estimates.get(p, 0.0) for p in party_order])
        f.write(f"mean_shares: {mean_shares}\n")
        f.write(f"sum = {np.sum(mean_shares)}\n")
        
        R = context.registered_voters or 6450523
        n_eff = max(100, engine._compute_effective_sample_size(context))
        f.write(f"n_eff = {n_eff}\n")
        
        alpha_base = np.array([estimates.get(p, 0.0) for p in party_order]) * n_eff
        alpha_base = np.maximum(alpha_base, 0.1)
        f.write(f"alpha_base: {alpha_base}\n")
        
        # Test first sim
        alpha = alpha_base.copy()
        top2_idx = np.argsort(np.array([estimates.get(p, 0.0) for p in party_order]))[-2:]
        f.write(f"top2_idx = {top2_idx} ({party_order[top2_idx[0]]}, {party_order[top2_idx[1]]})\n")
        
        swing = np.random.normal(0, 0.045)
        swing_conc = swing * 5757
        f.write(f"swing = {swing:.4f}, swing_conc = {swing_conc:.1f}\n")
        
        alpha_test = alpha_base.copy()
        alpha_test[top2_idx[0]] += swing_conc
        alpha_test[top2_idx[1]] -= swing_conc
        alpha_test = np.maximum(alpha_test, 0.1)
        f.write(f"alpha after swing: {alpha_test}\n")
        
        sample = np.random.dirichlet(alpha_test)
        f.write(f"Sample: " + ", ".join(f"{party_order[i]}={v*100:.1f}%" for i, v in enumerate(sample)) + "\n")
        
        # Call original
        return original_mc(context, estimates)

engine._run_monte_carlo_full = debug_mc

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

# Run simulation
engine.run_simulation(context)

print("Done - check debug_engine_mc.txt")