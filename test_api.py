import os
import sys
import json
sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

response = client.post(
    "/api/simulation/run",
    json={
        "election_id": 3,
        "n_simulations": 100,
        "threshold": 3,
        "total_seats": 250,
        "turnout": 60,
        "polls": [],
        "odds": []
    }
)

with open('api_full_response.json', 'w', encoding='utf-8') as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=2)

data = response.json()
lines = []
lines.append(f"Status: {response.status_code}")
lines.append(f"Data source: {data['metadata'].get('data_source')}")
lines.append(f"Registered voters: {data['metadata'].get('registered_voters')}")
lines.append(f"Counting path steps: {data['metadata'].get('counting_path', {}).get('steps')}")
lines.append(f"\nParties ({len(data['parties'])}):")
for p in data['parties']:
    votes = p.get('votes_mean', 'N/A')
    lines.append(f"  BN={p['ballot_number']:2d} MIN={str(p['is_minority']):5s} GOV={str(p['is_governing']):5s} | {p['short_name'][:30]:30s} | pct={p['vote_share_mean']:.1f}% votes={votes} seats={p['seats_mean']:.1f}")

with open('test_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Done - check test_output.txt")