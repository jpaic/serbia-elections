#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Primeni šemu baze (kreira nove tabele polls i market_lines)."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
load_dotenv()


def main():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")

    c = psycopg2.connect(DATABASE_URL)
    c.autocommit = True
    cur = c.cursor()

    statements = [
        """CREATE TABLE polls (
            id SERIAL PRIMARY KEY,
            election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
            pollster VARCHAR(100) NOT NULL,
            fieldwork_start DATE,
            fieldwork_end DATE,
            published DATE NOT NULL,
            sample_size INTEGER,
            basis VARCHAR(20) NOT NULL DEFAULT 'decided',
            turnout_pct NUMERIC(5,2),
            percentages JSONB NOT NULL,
            others_pct NUMERIC(5,2),
            weight NUMERIC(4,2) NOT NULL DEFAULT 1.0,
            source_url TEXT NOT NULL,
            notes TEXT
        )""",
        "CREATE INDEX idx_polls_election ON polls(election_id)",
        "CREATE INDEX idx_polls_published ON polls(published)",
        """CREATE TABLE market_lines (
            id SERIAL PRIMARY KEY,
            election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
            bookmaker VARCHAR(100) NOT NULL,
            observed DATE NOT NULL,
            market VARCHAR(30) NOT NULL,
            subject TEXT NOT NULL,
            value NUMERIC(8,3) NOT NULL,
            weight NUMERIC(4,2) NOT NULL DEFAULT 1.0,
            source_url TEXT NOT NULL
        )""",
        "CREATE INDEX idx_market_lines_election ON market_lines(election_id)",
        "CREATE INDEX idx_market_lines_market ON market_lines(market)",
    ]

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            print(f"OK: {stmt[:80]}...")
        except psycopg2.errors.DuplicateTable:
            print(f"SKIP (vec postoji): {stmt[:80]}...")
        except Exception as e:
            print(f"ERROR: {stmt[:80]}... -> {e}")

    # Proveri tabele
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name IN ('polls', 'market_lines')
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nKreirane tabele: {tables}")

    c.close()
    print("\nGotovo.")


if __name__ == "__main__":
    main()