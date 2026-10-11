import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

cur.execute("SELECT id, name, short_name, ballot_number, is_minority FROM parties WHERE election_id=3 ORDER BY ballot_number")
with open('db_check.txt', 'w', encoding='utf-8') as f:
    for r in cur.fetchall():
        f.write(f"ID={r[0]} BN={r[3]} MIN={r[4]} SHORT={r[2]}\nNAME={r[1]}\n\n")

c.close()
print("Done - check db_check.txt")