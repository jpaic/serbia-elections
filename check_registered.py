import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

# Check registered_voters for 2026
cur.execute("SELECT id, slug, name, registered_voters FROM elections WHERE slug='parlamentarni-2026'")
row = cur.fetchone()
print(f"Election: {row}")

if row[3] != 6450523:
    print(f"Updating registered_voters from {row[3]} to 6450523")
    cur.execute("UPDATE elections SET registered_voters=6450523 WHERE id=%s", (row[0],))
    print("Updated.")
else:
    print("Already correct.")

# Verify
cur.execute("SELECT registered_voters FROM elections WHERE slug='parlamentarni-2026'")
print(f"Current registered_voters: {cur.fetchone()[0]}")

c.close()