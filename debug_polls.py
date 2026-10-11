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

with open('debug_polls_output.txt', 'w', encoding='utf-8') as f:
    f.write("Parties:\n")
    for p in parties:
        f.write(f"  BN={p['ballot_number']} | {p['short_name'][:60]}\n")

    f.write("\nPolls:\n")
    for p in polls:
        f.write(f"  {p['pollster']} ({p['date']}): {p['percentages']}\n")

# Now test engine
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
with open('debug_polls_output.txt', 'w', encoding='utf-8') as f:
    f.write("Poll estimates:\n")
    for k, v in sorted(poll_estimates.items(), key=lambda x: -x[1]):
        f.write(f"  {k[:50]:50s} -> {v*100:.1f}%\n")

    filled = engine._fill_missing_parties(poll_estimates, context)
    f.write("\nAfter fill_missing:\n")
    for k, v in sorted(filled.items(), key=lambda x: -x[1]):
        f.write(f"  {k[:50]:50s} -> {v*100:.1f}%\n")

    normalized = engine._normalize_estimates(filled)
    f.write("\nAfter normalize:\n")
    for k, v in sorted(normalized.items(), key=lambda x: -x[1]):
        f.write(f"  {k[:50]:50s} -> {v*100:.1f}%\n")

print("Done - check debug_polls_output.txt")