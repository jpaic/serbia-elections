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

# Monkey-patch fill_missing to debug
original_fill = engine._fill_missing_parties
def debug_fill(estimates, context):
    with open('debug_fill_output.txt', 'w', encoding='utf-8') as f:
        f.write("=== fill_missing debug ===\n")
        f.write(f"estimates: {dict(sorted(estimates.items(), key=lambda x: -x[1]))}\n")
        f.write(f"poll_sum = {sum(estimates.values())}\n")
        
        priors = {
            "ДАЧИЋ": 5.0, "СДП": 2.0, "PÁSZTOR": 2.0, "SPP": 2.0,
            "РУСКА СТРАНКА": 1.5, "НАДА": 2.0, "СДА": 2.0,
            "ЗАВЕТНИ": 1.5, "ДЖБ": 1.5, "МИ ГЛАС": 1.0, "ССП": 1.0,
            "ЕВРОПСКА": 2.0, "ИЗБОР НАРОДА": 2.0, "КАРИЋ": 1.5,
            "ГРУПА ГРАЂАНА": 1.0, "ЛИБЕРАЛНО": 1.0, "БИРАМ": 1.0,
            "РУСКО СРПСКОГ": 1.0, "ЋАЛЕ ОВО": 0.5, "ГАЈИЋ": 1.0,
        }
        
        filled = dict(estimates)
        poll_sum = sum(estimates.values())
        remaining = max(0.0, 1.0 - poll_sum)
        f.write(f"poll_sum = {poll_sum}, remaining = {remaining}\n")
        
        missing_weights = {}
        for party in context.parties:
            in_filled = party.short_name in filled
            filled_val = filled.get(party.short_name, 'NOT_IN_FILLED')
            cond = party.short_name not in filled or filled[party.short_name] == 0.0
            f.write(f"Party: '{party.short_name[:50]}' | in_filled={in_filled} | filled_val={filled_val} | cond={cond}\n")
            if cond:
                prior = 0.1
                for key, val in priors.items():
                    if key in party.short_name.upper():
                        prior = val
                        break
                missing_weights[party.short_name] = prior
                f.write(f"  -> prior={prior}, key matched\n")
        
        f.write(f"missing_weights: {missing_weights}\n")
        total_missing_weight = sum(missing_weights.values())
        f.write(f"total_missing_weight = {total_missing_weight}, remaining = {remaining}\n")
        if total_missing_weight > 0 and remaining > 0:
            scale = remaining / total_missing_weight
            f.write(f"scale = {scale}\n")
            for name, weight in missing_weights.items():
                filled[name] = weight * scale / 100.0
                f.write(f"  filled['{name}'] = {filled[name]*100:.2f}%\n")
        
        f.write(f"Final filled: {dict(sorted(filled.items(), key=lambda x: -x[1]))}\n")
        return filled

engine._fill_missing_parties = debug_fill

poll_estimates = engine._compute_poll_estimates(context)
filled = engine._fill_missing_parties(poll_estimates, context)

with open('debug_fill_result.txt', 'w', encoding='utf-8') as f:
    f.write("Final filled after fill_missing:\n")
    for k, v in sorted(filled.items(), key=lambda x: -x[1]):
        f.write(f"  {k[:50]:50s} -> {v*100:.1f}%\n")

print("Done - check debug_fill_output.txt and debug_fill_result.txt")