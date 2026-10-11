import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
c = psycopg2.connect(os.environ["DATABASE_URL"])
c.autocommit = True
cur = c.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
print("Tables:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT count(*) FROM polls WHERE election_id=3")
print("Polls:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM market_lines WHERE election_id=3")
print("Market lines:", cur.fetchone()[0])
c.close()