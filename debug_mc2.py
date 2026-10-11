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

poll_estimates = engine._compute_poll_estimates(context)
filled = engine._fill_missing_parties(poll_estimates, context)
normalized = engine._normalize_estimates(filled)

party_order = [p.short_name for p in context.parties]
mean_shares = np.array([normalized.get(p, 0.0) for p in [p.short_name for p in context.parties]])

with open('debug_mc2_output.txt', 'w', encoding='utf-8') as f:
    f.write("Normalized estimates:\n")
    for p in context.parties:
        val = normalized.get(p.short_name, 0)
        f.write(f"  {p.short_name[:50]:50s} -> {val*100:.1f}%\n")

    n_eff = max(100, engine._compute_effective_sample_size(context))
    f.write(f"\nn_eff = {n_eff}\n")

    alpha_base = mean_shares * n_eff
    alpha_base = np.maximum(alpha_base, 0.1)

    f.write(f"\nalpha_base:\n")
    for i, p in enumerate(context.parties):
        f.write(f"  {p.short_name[:50]:50s} mean={mean_shares[i]*100:.1f}% alpha={alpha_base[i]:.1f}\n")

    # Test Dirichlet sampling
    f.write("\nDirichlet samples (5 sims):\n")
    for i in range(5):
        sample = np.random.dirichlet(alpha_base)
        top3 = sorted(zip([p.short_name for p in context.parties], sample), key=lambda x: -x[1])[:3]
        f.write(f"  Sim {i}: " + ", ".join(f"{n}={v*100:.1f}%" for n,v in top3) + "\n")