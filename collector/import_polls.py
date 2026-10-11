#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Idempotentni uvoz istraživanja i tržišnih linija za 2026."""
import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
load_dotenv()

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "polls_2026.json")


def main():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    c = psycopg2.connect(DATABASE_URL)
    c.autocommit = True
    cur = c.cursor()

    # Dohvati election_id za parlamentarni-2026
    cur.execute("SELECT id FROM elections WHERE slug='parlamentarni-2026'")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Election 'parlamentarni-2026' not found")
    eid = row[0]
    print(f"Election ID: {eid}")

    # Učitaj podatke
    with open(DATA_FILE, encoding='utf-8') as f:
        data = json.load(f)

    # Uvoz polls
    print("\n--- UVOZ POLLS ---")
    for p in data.get("polls", []):
        cur.execute("""
            INSERT INTO polls (election_id, pollster, fieldwork_start, fieldwork_end, published,
                               sample_size, basis, turnout_pct, percentages, others_pct,
                               weight, source_url, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            eid,
            p["pollster"],
            p.get("fieldwork_start"),
            p.get("fieldwork_end"),
            p["published"],
            p.get("sample_size"),
            p.get("basis", "decided"),
            p.get("turnout_pct"),
            json.dumps(p["percentages"]),
            p.get("others_pct"),
            p.get("weight", 1.0),
            p["source_url"],
            p.get("notes")
        ))
        if cur.rowcount:
            print(f"  + {p['pollster']} ({p['published']})")
        else:
            print(f"  = {p['pollster']} ({p['published']}) već postoji")

    # Uvoz market_lines
    print("\n--- UVOZ MARKET_LINES ---")
    for m in data.get("market_lines", []):
        cur.execute("""
            INSERT INTO market_lines (election_id, bookmaker, observed, market, subject, value, weight, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            eid,
            m["bookmaker"],
            m["observed"],
            m["market"],
            m["subject"],
            m["value"],
            m.get("weight", 1.0),
            m["source_url"]
        ))
        if cur.rowcount:
            print(f"  + {m['bookmaker']} {m['market']} {m['subject']}={m['value']}")
        else:
            print(f"  = {m['bookmaker']} {m['market']} {m['subject']} već postoji")

    # Provera
    cur.execute("SELECT count(*) FROM polls WHERE election_id=%s", (eid,))
    print(f"\nUkupno polls: {cur.fetchone()[0]}")
    cur.execute("SELECT count(*) FROM market_lines WHERE election_id=%s", (eid,))
    print(f"Ukupno market_lines: {cur.fetchone()[0]}")

    c.close()
    print("\nGotovo.")


if __name__ == "__main__":
    main()