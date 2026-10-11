import os
import sys
import numpy as np
sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")

from main import app
from simulation.engine import ElectionSimulationEngine
from simulation.models import ElectionContext, PartyData, PollData
from db import get_db_connection

conn_gen = get_db_connection()
conn = next(conn_gen)

from simulation.api import get_party_data, get_latest_polls

parties = get_party_data(3, conn)
polls = get_latest_polls(3, conn)

lines = []
lines.append(f"Parties: {len(parties)}")
for p in parties:
    lines.append(f"  {p['short_name'][:40]} -> ballot={p['ballot_number']}")

lines.append(f"\nPolls: {len(polls)}")
for poll in polls:
    lines.append(f"  {poll['pollster']} ({poll['date']}): {poll['percentages']}")

engine = ElectionSimulationEngine(n_simulations=100, turnout=60)

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
    total_seats=250
)

poll_estimates = engine._compute_poll_estimates(context)
lines.append("\n--- Poll Estimates (weighted average) ---")
for party, pct in sorted(poll_estimates.items(), key=lambda x: -x[1]):
    lines.append(f"  {party[:40]:40s} -> {pct*100:.1f}%")

alpha = engine._estimate_dirichlet_params(poll_estimates, context.parties)
lines.append("\n--- Alpha Params ---")
for party, a in sorted(alpha.items(), key=lambda x: -x[1]):
    mean = poll_estimates.get(party, 0)
    lines.append(f"  {party[:40]:40s} -> alpha={a:.1f}, mean={mean*100:.1f}%")

lines.append("\n--- Sample Simulations ---")
for i in range(5):
    alpha_vec = np.array([alpha.get(p.short_name, 0.1) for p in context.parties])
    vote_shares = np.random.dirichlet(alpha_vec)
    top3 = sorted(zip([p.short_name for p in context.parties], vote_shares), key=lambda x: -x[1])[:3]
    lines.append(f"  Sim {i}: " + ", ".join(f"{n}={v*100:.1f}%" for n,v in top3))

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

conn.close()
print("Done - check debug_output.txt")