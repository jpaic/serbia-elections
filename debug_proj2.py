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

original_proj = engine._compute_projections

def debug_proj(results, parties):
    with open('debug_proj_output.txt', 'w', encoding='utf-8') as f:
        f.write("=== _compute_projections debug ===\n")
        f.write(f"results keys: {results.keys()}\n")
        f.write(f"vote_shares shape: {results['vote_shares'].shape}\n")
        f.write(f"seats shape: {results['seats'].shape}\n")
        f.write(f"votes shape: {results['votes'].shape}\n")
        f.write(f"party_order: {results['party_order']}\n")
        f.write(f"parties: {[p.short_name for p in parties]}\n")
        
        party_order = results['party_order']
        party_idx = {p.short_name: i for i, p in enumerate(parties)}
        f.write(f"party_idx: {party_idx}\n")
        
        for party in parties:
            idx = party_idx[party.short_name]
            f.write(f"\nParty: {party.short_name[:40]} idx={idx}\n")
            f.write(f"  vote_shares[:, idx] shape: {results['vote_shares'][:, idx].shape}\n")
            f.write(f"  vote_shares[:, idx][:5]: {results['vote_shares'][:5, idx]}\n")
            f.write(f"  seats[:, idx][:5]: {results['seats'][:5, idx]}\n")
            f.write(f"  votes[:, idx][:5]: {results['votes'][:5, idx]}\n")
        
        return original_proj(results, parties)

engine._compute_projections = debug_proj

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

print("Done - check debug_proj_output.txt")