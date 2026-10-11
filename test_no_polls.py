import sys
sys.path.insert(0, r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test with empty polls - should return 422
response = client.post(
    "/api/simulation/run",
    json={
        "election_id": 3,
        "n_simulations": 100,
        "threshold": 3,
        "total_seats": 250,
        "turnout": 62,
        "polls": [],  # Empty polls
        "odds": []
    }
)

with open('test_no_polls_result.txt', 'w', encoding='utf-8') as f:
    f.write(f"Status: {response.status_code}\n")
    try:
        f.write(str(response.json()))
    except:
        f.write(response.text)

print("Done - check test_no_polls_result.txt")