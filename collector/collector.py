"""
Data collector — periodično povlači rezultate sa RIK-a po biračkom mestu i upisuje u PostgreSQL.

Arhitektura nakon discover.py:
  - RIK menja rik_station_id svaki krug (isto fizičko mesto ima različit id 2023 vs 2026)
  - get_results filtrira samo na nivou biračkog mesta (region/opština vraćaju nacionalni zbir)
  - Zato ide: election_station_codes (election_id, polling_station_id, rik_station_id) + rik_client

Pokretanje:
    pip install requests beautifulsoup4 sqlalchemy psycopg[binary] --break-system-packages
    export DATABASE_URL=postgresql://user:pass@host:5432/izbori
    # jednokratno pre prvog collectora (ili za istorijske izbore):
    python bootstrap.py --election-type 2 --election-round 341140 --election-date 2023-12-17
    python bootstrap.py --election-type 2 --election-round 680072 --election-date 2026-10-25
    # collector:
    python collector.py --election-id 1 --interval 45
    python collector.py --election-id 1 --once
"""
import argparse
import os
import time
import logging
from datetime import datetime

from sqlalchemy import create_engine, text

from rik_client import create_session, get_results_raw, parse_table_data, parse_stat_sum

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("collector")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _parse_won_number(s) -> int:
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


def fetch_raw_results(election_id: int, limit_stations: int | None = None, skip_processed: bool = True, delay: float = 0.35) -> list[dict]:
    """
    Povlači sve biračka mesta za dati election_id preko election_station_codes.
    Rate limited (delay između get_results), preskače već obrađena ako skip_processed.
    Vraća listu redova u obliku koji očekuje upsert_results.
    """
    with engine.connect() as conn:
        election = conn.execute(text("SELECT id, rik_type, rik_round, name FROM elections WHERE id = :id"), {"id": election_id}).fetchone()
        if not election:
            raise ValueError(f"Izbori id={election_id} ne postoje (pokreni bootstrap.py prvo)")
        if election.rik_type is None or election.rik_round is None:
            raise ValueError(f"Izbori id={election_id} nemaju rik_type/rik_round (popuni bootstrap.py)")

        rik_type = int(election.rik_type)
        rik_round = int(election.rik_round)

        # učitaj mapu station -> rik id
        rows = conn.execute(text("""
            SELECT esc.rik_station_id, esc.polling_station_id,
                   ps.name as station_name, m.name as mun_name, m.region
            FROM election_station_codes esc
            JOIN polling_stations ps ON ps.id = esc.polling_station_id
            JOIN municipalities m ON m.id = ps.municipality_id
            WHERE esc.election_id = :eid
            ORDER BY esc.rik_station_id
        """), {"eid": election_id}).fetchall()

        if not rows:
            raise ValueError(f"Nema election_station_codes za election_id={election_id} (pokreni bootstrap.py)")

        # opciono preskoči već obrađena mesta (brže na dan izbora: ~8000 mesta)
        to_fetch = []
        if skip_processed:
            existing = conn.execute(text("""
                SELECT DISTINCT polling_station_id FROM results
                WHERE election_id = :eid AND is_processed = true
            """), {"eid": election_id}).fetchall()
            processed_ids = {r.polling_station_id for r in existing}
            for r in rows:
                if r.polling_station_id not in processed_ids:
                    to_fetch.append(r)
            if not to_fetch:
                log.info("Sva biračka mesta već obrađena (%d), nema fetch-a", len(rows))
                return []
            log.info("Preskačem %d već obrađenih, fetchujem %d preostalih", len(processed_ids), len(to_fetch))
        else:
            to_fetch = rows

        if limit_stations:
            to_fetch = to_fetch[:limit_stations]
            log.info("Limit --limit-stations=%d", limit_stations)

    session = create_session()
    out: list[dict] = []
    total = len(to_fetch)

    for idx, r in enumerate(to_fetch, start=1):
        rik_sid = int(r.rik_station_id)
        # RIK zahteva pun cascading payload, ali get_results na nivou stanice
        # radi i samo sa election_station (ostali su opciono). Ipak šaljemo minimalno.
        try:
            raw = get_results_raw(session, rik_type, rik_round, station_id=rik_sid)
        except Exception as e:
            log.warning("[%d/%d] rik %s greška: %s", idx, total, rik_sid, e)
            continue

        if not raw:
            continue

        table = parse_table_data(raw)
        stat = parse_stat_sum(raw)
        is_processed = bool(stat.get("processed_stations")) and stat.get("processed_stations") != 0
        # Za neobrađena mesta table_data su nule/null - i dalje upisujemo kao not processed
        if not is_processed:
            # na dan izbora mnoga mesta još nisu obrađena - upiši jedan red po partiji sa is_processed=false
            # da frontend zna da je mesto postoji ali bez rezultata
            for row in table:
                votes = _parse_won_number(row.get("won_number"))
                if votes is None:
                    votes = 0
                # ako su svi na 0 i won_percent null, to je neobrađeno
                out.append({
                    "polling_station_id": int(r.polling_station_id),
                    "rik_station_id": rik_sid,
                    "party_ballot_number": int(row["ballot_number"]),
                    "votes": votes,
                    "valid_ballots": stat.get("valid"),
                    "invalid_ballots": stat.get("invalid"),
                    "total_voted": stat.get("available"),
                    "is_processed": False,
                })
            # takođe slučaj 2026 gde je raw prazan / 500 -> raw={} već preskočen gore
        else:
            for row in table:
                votes = _parse_won_number(row.get("won_number"))
                out.append({
                    "polling_station_id": int(r.polling_station_id),
                    "rik_station_id": rik_sid,
                    "party_ballot_number": int(row["ballot_number"]),
                    "votes": votes,
                    "valid_ballots": stat.get("valid"),
                    "invalid_ballots": stat.get("invalid"),
                    "total_voted": stat.get("available"),
                    "is_processed": True,
                })

        if idx % 100 == 0:
            log.info("Fetch %d/%d...", idx, total)

    log.info("Fetch gotov: %d redova za %d biračkih mesta", len(out), total)
    return out


def validate(raw_results: list[dict]) -> list[dict]:
    clean = []
    for row in raw_results:
        if row.get("votes", 0) < 0:
            log.warning("Preskačem negativan broj glasova: %s", row)
            continue
        if row.get("total_voted") and row.get("valid_ballots"):
            if row["total_voted"] < row["valid_ballots"]:
                log.warning("Neuklopivi total_voted/valid_ballots: %s", row)
                continue
        clean.append(row)
    return clean


def upsert_results(election_id: int, rows: list[dict]) -> int:
    # rows sada nose polling_station_id direktno (stabilno), ne rik_station_code
    # ali podrži i stari format sa rik_station_code za kompatibilnost
    updated = 0
    with engine.begin() as conn:
        for row in rows:
            ps_id = row.get("polling_station_id")
            if ps_id is None:
                # fallback: reši preko election_station_codes
                rik_sid = row.get("rik_station_id") or row.get("rik_station_code")
                if rik_sid is None:
                    continue
                try:
                    rik_sid_int = int(str(rik_sid).split("-")[-1]) if isinstance(rik_sid, str) and "-" in rik_sid else int(rik_sid)
                except ValueError:
                    continue
                found = conn.execute(text(
                    "SELECT polling_station_id FROM election_station_codes WHERE election_id=:eid AND rik_station_id=:rid"
                ), {"eid": election_id, "rid": rik_sid_int}).fetchone()
                if not found:
                    log.warning("Nepoznat rik_station_id: %s", rik_sid)
                    continue
                ps_id = found.polling_station_id

            party = conn.execute(text(
                "SELECT id FROM parties WHERE election_id = :eid AND ballot_number = :n"
            ), {"eid": election_id, "n": row["party_ballot_number"]}).fetchone()
            if not party:
                log.warning("Nepoznata lista broj %s", row["party_ballot_number"])
                continue

            conn.execute(text("""
                INSERT INTO results
                    (election_id, polling_station_id, party_id, votes,
                     valid_ballots, invalid_ballots, total_voted, is_processed, ingested_at)
                VALUES
                    (:eid, :sid, :pid, :votes, :valid, :invalid, :total, :processed, :now)
                ON CONFLICT (election_id, polling_station_id, party_id)
                DO UPDATE SET
                    votes = EXCLUDED.votes,
                    valid_ballots = EXCLUDED.valid_ballots,
                    invalid_ballots = EXCLUDED.invalid_ballots,
                    total_voted = EXCLUDED.total_voted,
                    is_processed = EXCLUDED.is_processed,
                    ingested_at = EXCLUDED.ingested_at
            """), {
                "eid": election_id,
                "sid": int(ps_id),
                "pid": party.id,
                "votes": row["votes"],
                "valid": row.get("valid_ballots"),
                "invalid": row.get("invalid_ballots"),
                "total": row.get("total_voted"),
                "processed": row.get("is_processed", False),
                "now": datetime.utcnow(),
            })
            updated += 1
    return updated


def log_ingestion(election_id: int, source: str, stations_updated: int, success: bool, error: str = None):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ingestion_log (election_id, source, stations_updated, success, error_message)
            VALUES (:eid, :source, :count, :success, :error)
        """), {"eid": election_id, "source": source, "count": stations_updated, "success": success, "error": error})


def run_once(election_id: int, limit_stations=None, skip_processed=True):
    try:
        raw = fetch_raw_results(election_id, limit_stations=limit_stations, skip_processed=skip_processed)
        clean = validate(raw)
        count = upsert_results(election_id, clean)
        # broj biračkih mesta je dedupl. po polling_station_id
        stations = len({r.get("polling_station_id") or r.get("rik_station_id") for r in clean}) if clean else 0
        log_ingestion(election_id, "rik_api", stations, True)
        log.info("Ažurirano %d redova (%d biračkih mesta)", count, stations)
    except Exception as e:
        log.exception("Greška pri povlačenju podataka")
        log_ingestion(election_id, "rik_api", 0, False, str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--election-id", type=int, required=True, help="ID iz elections tabele (ne rik_round)")
    ap.add_argument("--interval", type=int, default=45, help="Sekunde između povlačenja (30-60 preporučeno)")
    ap.add_argument("--once", action="store_true", help="Pokreni samo jednom, bez petlje")
    ap.add_argument("--limit-stations", type=int, default=None, help="Ograniči broj biračkih mesta (debug)")
    ap.add_argument("--no-skip", action="store_true", help="Ne preskači već obrađena mesta")
    args = ap.parse_args()

    if args.once:
        run_once(args.election_id, limit_stations=args.limit_stations, skip_processed=not args.no_skip)
        return

    log.info("Collector pokrenut, interval %ds", args.interval)
    while True:
        run_once(args.election_id, limit_stations=args.limit_stations, skip_processed=not args.no_skip)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
