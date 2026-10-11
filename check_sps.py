import sys
sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
res = client.post('/api/simulation/run', json={'election_id': 3, 'n_simulations': 2000, 'threshold': 3, 'total_seats': 250, 'turnout': 62, 'polls': [], 'odds': []})
data = res.json()

# Check deterministic seats
nat = data['metadata'].get('national', {})
det_seats = nat.get('deterministic_seats', {})
det_eligible = nat.get('deterministic_eligible', {})

# Find SPS short_name
sps_short = None
for p in data['parties']:
    if p['ballot_number'] == 2:
        sps_short = p['short_name']
        print(f"SPS: pct={p['vote_share_mean']:.1f}%, threshold_cleared_prob={p['threshold_cleared_prob']:.2f}, seats_mean={p['seats_mean']:.1f}")
        break

if sps_short:
    print(f"Deterministic: eligible={det_eligible.get(sps_short)}, seats={det_seats.get(sps_short)}")

print("\nAll deterministic seats:")
for name, seats in sorted(det_seats.items(), key=lambda x: -x[1]):
    if seats > 0:
        print(f"  {name[:40]:40s} -> {seats} seats (eligible={det_eligible.get(name)})")