import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

cur.execute("SELECT short_name, ballot_number FROM parties WHERE election_id=3 ORDER BY ballot_number")

with open('short_names.txt', 'w', encoding='utf-8') as f:
    for r in cur.fetchall():
        f.write(f"BN={r[1]:2d} | {r[0]}\n")

c.close()
print("Done - check short_names.txt")