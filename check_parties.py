import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()
cur.execute("SELECT ballot_number, short_name, is_minority FROM parties WHERE election_id=3 ORDER BY ballot_number")

with open('party_list.txt', 'w', encoding='utf-8') as f:
    for r in cur.fetchall():
        f.write(f"BN={r[0]} MIN={r[2]} | {r[1][:80]}\n")

c.close()
print("Done - check party_list.txt")