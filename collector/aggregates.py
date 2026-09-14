"""
Agregatni collector — izborna noć za <10 minuta.

Umesto 8273 poziva po biračkom mestu: ~200 poziva
(1 nacionalni + 7 regiona-liste + ~193 opštine) jer get_results sa KRATKIM
parametrima (type/region/municipality) zaista filtrira.
Upisuje municipality_stats + municipality_results (+ election_municipality_codes).

Pokretanje:
    python aggregates.py --election-id 2 --once
    python aggregates.py --election-id 2 --interval 60
"""
import argparse
import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import create_engine, text

# DATABASE_URL iz backend/.env da se ne mora rucno exportovati (radi iz repo root-a)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    for _p in (Path("backend/.env"), Path(__file__).parent.parent / "backend" / ".env"):
        if _p.exists():
            load_dotenv(_p)
            break
except ImportError:
    pass

from rik_client import (
    create_session, get_regions, get_municipalities,
    get_results_agg, parse_table_data, parse_stat_sum,
)
from bootstrap import ensure_party

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aggregates")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=10)

_thread_sessions = threading.local()


def thread_session():
    s = getattr(_thread_sessions, "s", None)
    if s is None:
        s = create_session()
        _thread_sessions.s = s
    return s


def _parse_int_loose(s) -> int:
    if s is None:
        return 0
    if isinstance(s, int):
        return s
    cleaned = str(s).replace(".", "").replace(",", "").replace("\xa0", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def upsert_municipality(election_id: int, municipality_id: int, table: list[dict], stat: dict):
    now = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO municipality_stats
                (election_id, municipality_id, total_voted, registered_voters,
                 valid_ballots, invalid_ballots, processed_stations, total_stations, ingested_at)
            VALUES (:eid, :mid, :voted, :reg, :valid, :invalid, :proc, :total, :now)
            ON CONFLICT (election_id, municipality_id) DO UPDATE SET
                total_voted = EXCLUDED.total_voted,
                registered_voters = EXCLUDED.registered_voters,
                valid_ballots = EXCLUDED.valid_ballots,
                invalid_ballots = EXCLUDED.invalid_ballots,
                processed_stations = EXCLUDED.processed_stations,
                total_stations = EXCLUDED.total_stations,
                ingested_at = EXCLUDED.ingested_at
        """), {
            "eid": election_id, "mid": municipality_id,
            "voted": stat.get("available"), "reg": stat.get("total_voters"),
            "valid": stat.get("valid"), "invalid": stat.get("invalid"),
            "proc": stat.get("processed_stations") or 0,
            "total": stat.get("total_stations") or 0,
            "now": now,
        })
        if not table:
            return 0
        party_rows = conn.execute(text(
            "SELECT id, ballot_number FROM parties WHERE election_id = :eid"
        ), {"eid": election_id}).fetchall()
        by_ballot = {p.ballot_number: p.id for p in party_rows}
        params = []
        for row in table:
            pid = by_ballot.get(int(row["ballot_number"]))
            if pid is None:
                continue
            params.append({"eid": election_id, "mid": municipality_id, "pid": pid,
                           "votes": _parse_int_loose(row.get("votes")), "now": now})
        if params:
            conn.execute(text("""
                INSERT INTO municipality_results (election_id, municipality_id, party_id, votes, ingested_at)
                VALUES (:eid, :mid, :pid, :votes, :now)
                ON CONFLICT (election_id, municipality_id, party_id)
                DO UPDATE SET votes = EXCLUDED.votes, ingested_at = EXCLUDED.ingested_at
            """), params)
        return len(params)


def fetch_one(args) -> tuple[str, bool]:
    """Obradi jednu opštinu: fetch + upis. Vraća (ime, uspeh)."""
    election_id, rik_type, rik_round, region_id, mun_value, mun_data_id, mun_name, municipality_id = args
    try:
        raw = get_results_agg(thread_session(), rik_type, rik_round,
                              region_id=region_id, municipality_value=mun_value)
        if not raw:
            return mun_name, False
        table = parse_table_data(raw)
        stat = parse_stat_sum(raw)
        upsert_municipality(election_id, municipality_id, table, stat)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO election_municipality_codes
                    (election_id, municipality_id, rik_region_id, rik_mun_value)
                VALUES (:eid, :mid, :rid, :mv)
                ON CONFLICT (election_id, municipality_id)
                DO UPDATE SET rik_region_id = EXCLUDED.rik_region_id,
                              rik_mun_value = EXCLUDED.rik_mun_value
            """), {"eid": election_id, "mid": municipality_id,
                   "rid": region_id, "mv": mun_value})
        return mun_name, True
    except Exception as e:
        log.warning("Opština %s greška: %s", mun_name, e)
        return mun_name, False


def run_once(election_id: int, workers: int = 6):
    t0 = time.time()
    with engine.connect() as conn:
        election = conn.execute(
            text("SELECT id, rik_type, rik_round, name FROM elections WHERE id = :id"),
            {"id": election_id}).fetchone()
        if not election or election.rik_type is None or election.rik_round is None:
            raise ValueError(f"Izbori id={election_id} nemaju rik_type/rik_round")
        rik_type, rik_round = int(election.rik_type), int(election.rik_round)

    session = create_session()
    regions = (get_regions(session, rik_type, rik_round).get("regions") or {})

    # nacionalni poziv osigurava liste (parties)
    raw_national = get_results_agg(session, rik_type, rik_round)
    table_nat = parse_table_data(raw_national)
    if table_nat:
        with engine.begin() as conn:
            for row in table_nat:
                ensure_party(conn, election_id, row["ballot_number"], row["name"])

    # sakupi (region, municipality) zadatke; match DB po rzs_code (data-id)
    tasks = []
    with engine.connect() as conn:
        for region_id_str, region_name in regions.items():
            try:
                region_id = int(region_id_str)
            except ValueError:
                continue
            try:
                muns = get_municipalities(session, rik_type, rik_round, region_id)
            except Exception as e:
                log.warning("Region %s greška: %s", region_id, e)
                continue
            for mun in muns:
                data_id = str(mun.get("data_id") or "")
                found = conn.execute(text(
                    "SELECT id FROM municipalities WHERE rzs_code = :c"
                ), {"c": data_id}).fetchone() if data_id else None
                if not found:
                    # fallback po imenu+regionu
                    found = conn.execute(text(
                        "SELECT id FROM municipalities WHERE name = :n AND region = :r"
                    ), {"n": mun["name"], "r": region_name}).fetchone()
                if not found:
                    log.warning("Opština %s (%s) nije u bazi — preskačem (pokreni bootstrap)", mun["name"], data_id)
                    continue
                tasks.append((election_id, rik_type, rik_round, region_id,
                              mun["value"], data_id, mun["name"], found.id))

    log.info("Opština za fetch: %d (workera: %d)", len(tasks), workers)
    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (name, success) in enumerate(ex.map(fetch_one, tasks), start=1):
            if success:
                ok += 1
            if i % 50 == 0:
                log.info("Progres agregata: %d/%d...", i, len(tasks))
    dt = time.time() - t0
    log.info("Agregati gotovi: %d/%d opština za %.0fs", ok, len(tasks), dt)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ingestion_log (election_id, source, stations_updated, success, error_message)
            VALUES (:eid, 'rik_agg', :count, :success, :error)
        """), {"eid": election_id, "count": ok, "success": ok > 0,
               "error": None if ok else "nijedna opština nije uspela"})
    return ok


def resolve_election_id(election_id: int | None, slug: str | None) -> int:
    if election_id is not None:
        return election_id
    if not slug:
        raise SystemExit("Mora --election-id ili --election-slug")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM elections WHERE slug = :s"), {"s": slug}).fetchone()
    if not row:
        raise SystemExit(f"Nema izbora sa slug={slug!r}")
    return int(row.id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--election-id", type=int, default=None)
    ap.add_argument("--election-slug", type=str, default=None, help="npr. parlamentarni-2026")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    eid = resolve_election_id(args.election_id, args.election_slug)
    if args.once:
        run_once(eid, workers=args.workers)
        return
    log.info("Agregatni collector, interval %ds", args.interval)
    while True:
        try:
            run_once(eid, workers=args.workers)
        except Exception:
            log.exception("Greška u krugu")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
