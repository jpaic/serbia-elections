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
    return fetchall(
        """
        SELECT e.id, e.slug, e.name, e.election_type, e.election_date, e.status,
               COALESCE(s.proc, 0) AS stations_with_results,
               COALESCE(v.votes, 0) AS total_votes
        FROM elections e
        LEFT JOIN (
            SELECT election_id, SUM(processed_stations) AS proc
            FROM municipality_stats GROUP BY election_id
        ) s ON s.election_id = e.id
        LEFT JOIN (
            SELECT election_id, SUM(votes) AS votes
            FROM municipality_results GROUP BY election_id
        ) v ON v.election_id = e.id
        ORDER BY e.election_date DESC
        """
    )


@app.get("/elections/{election_id}/summary")
def election_summary(election_id: int):
    election = fetchone("SELECT * FROM elections WHERE id = :id", {"id": election_id})
    if not election:
        raise HTTPException(404, "Izbori nisu pronađeni")

    agg = fetchone(
        """
        SELECT
            COALESCE(SUM(total_stations), 0) AS total_stations,
            COALESCE(SUM(processed_stations), 0) AS processed_stations,
            COALESCE(SUM(total_voted), 0) AS total_voted,
            COALESCE(SUM(registered_voters), 0) AS total_registered
        FROM municipality_stats
        WHERE election_id = :eid
        """,
        {"eid": election_id},
    )

    party_totals = fetchall(
        """
        SELECT p.id, p.name, p.short_name, p.color_hex, COALESCE(SUM(mr.votes), 0) AS votes
        FROM parties p
        LEFT JOIN municipality_results mr ON mr.party_id = p.id AND mr.election_id = :eid
        WHERE p.election_id = :eid
        GROUP BY p.id, p.name, p.short_name, p.color_hex
        ORDER BY votes DESC
        """,
        {"eid": election_id},
    )

    total_stations = agg["total_stations"] or 0
    processed_stations = agg["processed_stations"] or 0
    total_votes = sum(p["votes"] for p in party_totals) or 0

    return {
        "election": election,
        "processed_pct": round(100 * processed_stations / total_stations, 2) if total_stations else 0,
        "turnout_pct": round(100 * (agg["total_voted"] or 0) / (agg["total_registered"] or 1), 2),
        "results": [
            {**p, "pct": round(100 * p["votes"] / total_votes, 2) if total_votes else 0}
            for p in party_totals
        ],
    }


@app.get("/elections/{election_id}/municipalities")
def municipalities_results(election_id: int):
    stations = fetchall(
        """
        SELECT
            m.id, m.name, m.region, m.rzs_code,
            COALESCE(ms.total_stations, 0) AS total_stations,
            COALESCE(ms.processed_stations, 0) AS processed_stations,
            COALESCE(ms.total_voted, 0) AS total_voted,
            COALESCE(ms.registered_voters, 0) AS registered_voters
        FROM municipalities m
        LEFT JOIN municipality_stats ms ON ms.municipality_id = m.id AND ms.election_id = :eid
        ORDER BY m.name
        """,
        {"eid": election_id},
    )

    party_rows = fetchall(
        """
        SELECT mr.municipality_id, p.id, p.name, p.short_name, p.color_hex, mr.votes
        FROM municipality_results mr
        JOIN parties p ON p.id = mr.party_id
        WHERE mr.election_id = :eid
        ORDER BY mr.municipality_id, mr.votes DESC
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
            COALESCE(SUM(ms.total_stations), 0) AS total_stations,
            COALESCE(SUM(ms.processed_stations), 0) AS processed_stations,
            COALESCE(SUM(ms.total_voted), 0) AS total_voted,
            COALESCE(SUM(ms.registered_voters), 0) AS registered_voters
        FROM municipalities m
        LEFT JOIN municipality_stats ms ON ms.municipality_id = m.id AND ms.election_id = :eid
        GROUP BY m.region
        """,
        {"eid": election_id},
    )

    party_rows = fetchall(
        """
        SELECT m.region AS region, p.id, p.name, p.short_name, p.color_hex, SUM(mr.votes) AS votes
        FROM municipality_results mr
        JOIN parties p ON p.id = mr.party_id
        JOIN municipalities m ON m.id = mr.municipality_id
        WHERE mr.election_id = :eid
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
            "total_voted": s["total_voted"] or 0,
            "registered_voters": s["registered_voters"] or 0,
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
        SELECT p.name, p.short_name, p.color_hex, mr.votes
        FROM municipality_results mr
        JOIN parties p ON p.id = mr.party_id
        WHERE mr.election_id = :eid AND mr.municipality_id = :mid
        ORDER BY mr.votes DESC
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
    from datetime import datetime
    from rik_live import fetch_station

    station = fetchone("SELECT * FROM polling_stations WHERE id = :id", {"id": station_id})
    if not station:
        raise HTTPException(404, "Biračko mesto nije pronađeno")

    # keš iz baze
    cached = fetchall(
        """
        SELECT p.name, p.short_name, r.votes, r.is_processed
        FROM results r
        JOIN parties p ON p.id = r.party_id
        WHERE r.election_id = :eid AND r.polling_station_id = :sid
        ORDER BY r.votes DESC
        """,
        {"eid": election_id, "sid": station_id},
    )
    if cached:
        return {"station": station, "results": cached, "live": False}

    # nema keša — povuci uživo sa RIK-a preko mapiranja i upiši
    mapping = fetchone(
        """
        SELECT e.rik_type, e.rik_round, emc.rik_region_id, emc.rik_mun_value,
               esc.rik_station_id
        FROM elections e
        JOIN election_municipality_codes emc
          ON emc.election_id = e.id AND emc.municipality_id = :mid
        JOIN election_station_codes esc
          ON esc.election_id = e.id AND esc.polling_station_id = :sid
        WHERE e.id = :eid
        """,
        {"eid": election_id, "mid": station["municipality_id"], "sid": station_id},
    )
    if not mapping or not mapping.get("rik_type") or not mapping.get("rik_round"):
        return {"station": station, "results": [], "live": False}

    try:
        live = fetch_station(
            int(mapping["rik_type"]), int(mapping["rik_round"]),
            int(mapping["rik_region_id"]), int(mapping["rik_mun_value"]),
            int(mapping["rik_station_id"]),
        )
    except Exception:
        return {"station": station, "results": [], "live": False}

    party_rows = fetchall(
        "SELECT id, ballot_number FROM parties WHERE election_id = :eid",
        {"eid": election_id},
    )
    by_ballot = {p["ballot_number"]: p["id"] for p in party_rows}
    params = [
        {"eid": election_id, "sid": station_id, "pid": by_ballot[row["ballot_number"]],
         "votes": row["votes"], "processed": bool(live["stat"].get("processed")),
         "now": datetime.utcnow()}
        for row in live["rows"]
        if row["ballot_number"] in by_ballot
    ]
    if params:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO results
                    (election_id, polling_station_id, party_id, votes, is_processed, ingested_at)
                VALUES (:eid, :sid, :pid, :votes, :processed, :now)
                ON CONFLICT (election_id, polling_station_id, party_id)
                DO UPDATE SET votes = EXCLUDED.votes,
                              is_processed = EXCLUDED.is_processed,
                              ingested_at = EXCLUDED.ingested_at
            """), params)

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
    return {"station": station, "results": results, "live": True}
