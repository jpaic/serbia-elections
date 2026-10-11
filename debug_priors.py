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

poll_estimates = engine._compute_poll_estimates(context)

with open('debug_priors_output.txt', 'w', encoding='utf-8') as f:
    f.write("Poll estimates keys:\n")
    for k in poll_estimates.keys():
        f.write(f"  '{k}'\n")

    f.write("\nContext parties short_names:\n")
    for p in context.parties:
        in_est = p.short_name in poll_estimates
        val = poll_estimates.get(p.short_name, 'NOT_IN_ESTIMATES')
        f.write(f"  BN={p.ballot_number:2d} | in_estimates={in_est} | val={val} | '{p.short_name[:60]}'\n")

    priors = {
        "ДАЧИЋ": 5.0, "СДП": 2.0, "PÁSZTOR": 2.0, "SPP": 2.0,
        "РУСКА СТРАНКА": 1.5, "НАДА": 2.0, "СДА": 2.0,
        "ЗАВЕТНИ": 1.5, "ДЖБ": 1.5, "МИ ГЛАС": 1.0, "ССП": 1.0,
        "ЕВРОПСКА": 2.0, "ИЗБОР НАРОДА": 2.0, "КАРИЋ": 1.5,
        "ГРУПА ГРАЂАНА": 1.0, "ЛИБЕРАЛНО": 1.0, "БИРАМ": 1.0,
        "РУСКО СРПСКОГ": 1.0, "ЋАЛЕ ОВО": 0.5, "ГАЈИЋ": 1.0,
    }

    f.write("\nPrior matching:\n")
    for p in context.parties:
        if p.short_name not in poll_estimates:
            matched = False
            for key, val in priors.items():
                if key in p.short_name.upper():
                    f.write(f"  MATCH: '{key}' in '{p.short_name[:60]}' -> prior={val}\n")
                    matched = True
                    break
            if not matched:
                f.write(f"  NO MATCH: '{p.short_name[:60]}'\n")

    f.write("\nDone\n")