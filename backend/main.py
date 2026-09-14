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

# Vercel services: frontend na /, backend na /api/backend -> backend dobija
# punu putanju (/api/backend/elections) pa je skidamo pre rutiranja.
# Ovo omogućava da lokalno radi na /elections, a na Vercelu na /api/backend/elections
@app.middleware("http")
async def strip_api_backend_prefix(request, call_next):
    path = request.scope.get("path", "")
    if path.startswith("/api/backend"):
        new_path = path[len("/api/backend"):]
        if not new_path.startswith("/"):
            new_path = "/" + new_path
        request.scope["path"] = new_path
        # za neke ASGI servere potrebno i raw_path
        if b"/api/backend" in request.scope.get("raw_path", b""):
            request.scope["raw_path"] = new_path.encode()
    return await call_next(request)

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
    return fetchall("SELECT id, slug, name, election_type, election_date, status FROM elections ORDER BY election_date DESC")


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
    stations = fetchall(
        """
        SELECT
            m.id, m.name, m.region, m.rzs_code,
            COUNT(DISTINCT ps.id) AS total_stations,
            COUNT(DISTINCT CASE WHEN r.is_processed THEN ps.id END) AS processed_stations,
            SUM(CASE WHEN r.is_processed THEN r.total_voted ELSE 0 END) AS total_voted,
            SUM(ps.registered_voters) AS registered_voters
        FROM municipalities m
        JOIN polling_stations ps ON ps.municipality_id = m.id
        LEFT JOIN results r ON r.polling_station_id = ps.id AND r.election_id = :eid
        GROUP BY m.id, m.name, m.region, m.rzs_code
        ORDER BY m.name
        """,
        {"eid": election_id},
    )

    party_rows = fetchall(
        """
        SELECT m.id AS municipality_id, p.id, p.name, p.short_name, p.color_hex, SUM(r.votes) AS votes
        FROM results r
        JOIN parties p ON p.id = r.party_id
        JOIN polling_stations ps ON ps.id = r.polling_station_id
        JOIN municipalities m ON m.id = ps.municipality_id
        WHERE r.election_id = :eid AND r.is_processed
        GROUP BY m.id, p.id, p.name, p.short_name, p.color_hex
        ORDER BY m.id, votes DESC
        """,
        {"eid": election_id},
    )

    by_mun: dict[int, list[dict]] = {}
    for row in party_rows:
        by_mun.setdefault(row["municipality_id"], []).append(row)

    out = []
    for s in stations:
        mid = s["id"]
        parties = by_mun.get(mid, [])
        total_votes = sum(p["votes"] for p in parties) or 0
        results = [
            {k: v for k, v in p.items() if k != "municipality_id"} | {"pct": round(100 * p["votes"] / total_votes, 2) if total_votes else 0}
            for p in parties
        ]
        leader = results[0] if results else None
        runner_up = results[1] if len(results) > 1 else None
        margin = (leader["pct"] - runner_up["pct"]) if (leader and runner_up) else (leader["pct"] if leader else 0)
        total_stations = s["total_stations"] or 0
        processed_stations = s["processed_stations"] or 0
        out.append({
            **s,
            "processed_pct": round(100 * processed_stations / total_stations, 2) if total_stations else 0,
            "turnout_pct": round(100 * (s["total_voted"] or 0) / (s["registered_voters"] or 1), 2),
            "leader": leader,
            "margin_pct": round(margin, 2),
            "results": results,
        })
    return out


@app.get("/elections/{election_id}/regions")
def regions_results(election_id: int):
    """
    Agregacija na nivou upravnog okruga (region): obrađenost biračkih mesta,
    izlaznost i rezultati po partiji, da bi mapa mogla da boji svaki okrug
    bojom vodeće partije (kao CNN/BBC/Fox election night mape) umesto samo
    procentom obrađenosti.
    """
    stations = fetchall(
        """
        SELECT
            m.region AS region,
            COUNT(DISTINCT ps.id) AS total_stations,
            COUNT(DISTINCT CASE WHEN r.is_processed THEN ps.id END) AS processed_stations,
            SUM(CASE WHEN r.is_processed THEN r.total_voted ELSE 0 END) AS total_voted,
            SUM(ps.registered_voters) AS registered_voters
        FROM municipalities m
        JOIN polling_stations ps ON ps.municipality_id = m.id
        LEFT JOIN results r ON r.polling_station_id = ps.id AND r.election_id = :eid
        GROUP BY m.region
        """,
        {"eid": election_id},
    )

    party_rows = fetchall(
        """
        SELECT m.region AS region, p.id, p.name, p.short_name, p.color_hex, SUM(r.votes) AS votes
        FROM results r
        JOIN parties p ON p.id = r.party_id
        JOIN polling_stations ps ON ps.id = r.polling_station_id
        JOIN municipalities m ON m.id = ps.municipality_id
        WHERE r.election_id = :eid AND r.is_processed
        GROUP BY m.region, p.id, p.name, p.short_name, p.color_hex
        ORDER BY m.region, votes DESC
        """,
        {"eid": election_id},
    )

    by_region: dict[str, list[dict]] = {}
    for row in party_rows:
        by_region.setdefault(row["region"], []).append(row)

    out = []
    for s in stations:
        region = s["region"]
        parties = by_region.get(region, [])
        total_votes = sum(p["votes"] for p in parties) or 0
        results = [
            {**p, "pct": round(100 * p["votes"] / total_votes, 2) if total_votes else 0}
            for p in parties
        ]
        leader = results[0] if results else None
        runner_up = results[1] if len(results) > 1 else None
        margin = (leader["pct"] - runner_up["pct"]) if (leader and runner_up) else (leader["pct"] if leader else 0)

        total_stations = s["total_stations"] or 0
        processed_stations = s["processed_stations"] or 0

        out.append({
            "region": region,
            "total_stations": total_stations,
            "processed_stations": processed_stations,
            "processed_pct": round(100 * processed_stations / total_stations, 2) if total_stations else 0,
            "turnout_pct": round(100 * (s["total_voted"] or 0) / (s["registered_voters"] or 1), 2),
            "leader": leader,
            "margin_pct": round(margin, 2),
            "results": results,
        })

    return out


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
