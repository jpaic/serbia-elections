"""
FastAPI backend za izborni dashboard.

Pokretanje lokalno:
    pip install fastapi uvicorn sqlalchemy psycopg[binary] --break-system-packages
    export DATABASE_URL=postgresql://user:pass@host:5432/izbori
    uvicorn main:app --reload

Deploy: Vercel (serverless) ili bilo koji host koji podržava ASGI (Render, Railway, Fly.io).
Za Vercel je najlakše preko vercel.json + fastapi adaptera; za realne servere sa dugoročnim
konekcijama i background poslom (collector) bolje je Railway/Fly/VM.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()  # čita .env fajl u istom folderu ako postoji (lokalni razvoj)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
# SQLAlchemy podrazumevano traži psycopg2 za "postgresql://" stringove; mi koristimo
# psycopg (v3) jer ima gotove binarne pakete za sve platforme (uključujući Windows +
# Python 3.13), pa ovde prebacujemo šemu bez da menjaš .env/Neon string ručno.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Izbori API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # suziti na domen frontenda u produkciji
    allow_methods=["GET"],
    allow_headers=["*"],
)


def fetchall(query, params=None):
    with engine.connect() as conn:
        rows = conn.execute(text(query), params or {})
        return [dict(r._mapping) for r in rows]


def fetchone(query, params=None):
    rows = fetchall(query, params)
    return rows[0] if rows else None


@app.get("/elections")
def list_elections():
    return fetchall("SELECT id, name, election_type, election_date, status FROM elections ORDER BY election_date DESC")


@app.get("/elections/{election_id}/summary")
def election_summary(election_id: int):
    election = fetchone("SELECT * FROM elections WHERE id = :id", {"id": election_id})
    if not election:
        raise HTTPException(404, "Izbori nisu pronađeni")

    processed = fetchone(
        """
        SELECT
            COUNT(DISTINCT ps.id) AS total_stations,
            COUNT(DISTINCT CASE WHEN r.is_processed THEN ps.id END) AS processed_stations
        FROM polling_stations ps
        LEFT JOIN results r ON r.polling_station_id = ps.id AND r.election_id = :eid
        """,
        {"eid": election_id},
    )

    turnout = fetchone(
        """
        SELECT
            SUM(r.total_voted) AS total_voted,
            SUM(ps.registered_voters) AS total_registered
        FROM results r
        JOIN polling_stations ps ON ps.id = r.polling_station_id
        WHERE r.election_id = :eid AND r.is_processed
        """,
        {"eid": election_id},
    )

    party_totals = fetchall(
        """
        SELECT p.id, p.name, p.short_name, p.color_hex, SUM(r.votes) AS votes
        FROM results r
        JOIN parties p ON p.id = r.party_id
        WHERE r.election_id = :eid AND r.is_processed
        GROUP BY p.id, p.name, p.short_name, p.color_hex
        ORDER BY votes DESC
        """,
        {"eid": election_id},
    )

    total_stations = processed["total_stations"] or 0
    processed_stations = processed["processed_stations"] or 0
    total_votes = sum(p["votes"] for p in party_totals) or 1

    return {
        "election": election,
        "processed_pct": round(100 * processed_stations / total_stations, 2) if total_stations else 0,
        "turnout_pct": round(100 * (turnout["total_voted"] or 0) / (turnout["total_registered"] or 1), 2),
        "results": [
            {**p, "pct": round(100 * p["votes"] / total_votes, 2)} for p in party_totals
        ],
    }


@app.get("/elections/{election_id}/municipalities")
def municipalities_results(election_id: int):
    return fetchall(
        """
        SELECT
            m.id, m.name, m.region,
            COUNT(DISTINCT ps.id) AS total_stations,
            COUNT(DISTINCT CASE WHEN r.is_processed THEN ps.id END) AS processed_stations,
            SUM(r.total_voted) AS total_voted,
            SUM(ps.registered_voters) AS registered_voters
        FROM municipalities m
        JOIN polling_stations ps ON ps.municipality_id = m.id
        LEFT JOIN results r ON r.polling_station_id = ps.id AND r.election_id = :eid
        GROUP BY m.id, m.name, m.region
        ORDER BY m.name
        """,
        {"eid": election_id},
    )


@app.get("/elections/{election_id}/municipalities/{municipality_id}")
def municipality_detail(election_id: int, municipality_id: int):
    municipality = fetchone("SELECT * FROM municipalities WHERE id = :id", {"id": municipality_id})
    if not municipality:
        raise HTTPException(404, "Opština nije pronađena")

    results = fetchall(
        """
        SELECT p.name, p.short_name, p.color_hex, SUM(r.votes) AS votes
        FROM results r
        JOIN parties p ON p.id = r.party_id
        JOIN polling_stations ps ON ps.id = r.polling_station_id
        WHERE r.election_id = :eid AND ps.municipality_id = :mid AND r.is_processed
        GROUP BY p.name, p.short_name, p.color_hex
        ORDER BY votes DESC
        """,
        {"eid": election_id, "mid": municipality_id},
    )
    total_votes = sum(r["votes"] for r in results) or 1

    return {
        "municipality": municipality,
        "results": [{**r, "pct": round(100 * r["votes"] / total_votes, 2)} for r in results],
    }


@app.get("/elections/{election_id}/polling-stations/{station_id}")
def polling_station_detail(election_id: int, station_id: int):
    station = fetchone("SELECT * FROM polling_stations WHERE id = :id", {"id": station_id})
    if not station:
        raise HTTPException(404, "Biračko mesto nije pronađeno")

    results = fetchall(
        """
        SELECT p.name, p.short_name, r.votes, r.is_processed
        FROM results r
        JOIN parties p ON p.id = r.party_id
        WHERE r.election_id = :eid AND r.polling_station_id = :sid
        ORDER BY r.votes DESC
        """,
        {"eid": election_id, "sid": station_id},
    )
    return {"station": station, "results": results}
