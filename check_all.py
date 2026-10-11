import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

# Check all parties with their IDs and ballot numbers
cur.execute("SELECT id, ballot_number, is_minority, name FROM parties WHERE election_id=3 ORDER BY ballot_number")

with open('all_parties.txt', 'w', encoding='utf-8') as f:
    for r in cur.fetchall():
        f.write(f"ID={r[0]} BN={r[1]} MIN={r[2]} | {r[3][:100]}\n")

c.close()
print("Done - check all_parties.txt")