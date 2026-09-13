"""
Data collector — periodično povlači rezultate i upisuje ih u PostgreSQL.

VAŽNO: RIK (rik.parlament.gov.rs) ne mora imati stabilan javni API u trenutku
kad ovo budeš pokretao uživo. Ova funkcija `fetch_raw_results()` je namerno
izolovana — to je JEDINO mesto koje treba promeniti kad utvrdiš stvarni format
(JSON endpoint, XML feed ili HTML koji treba parsirati). Sve ostalo
(validacija, upis u bazu, logovanje) ostaje isto.

Pre izbora, uživo proveriti:
  1. Da li RIK ima javni JSON/XML endpoint (pogledati Network tab u browseru
     na rik.parlament.gov.rs tokom prethodnih izbora / probne objave).
  2. Ako nema, da li postoji stabilna HTML struktura pogodna za scraping
     (BeautifulSoup) ili PDF izveštaji (u tom slučaju treba pdf ekstrakcija).
  3. RZS (stat.gov.rs) za matične šifre opština i broj registrovanih birača —
     ovo se povlači JEDNOM unapred, ne treba real-time.

Pokretanje:
    pip install requests sqlalchemy psycopg2-binary beautifulsoup4 --break-system-packages
    export DATABASE_URL=postgresql://user:pass@host:5432/izbori
    python collector.py --election-id 1 --interval 45
"""
import argparse
import time
import logging
from datetime import datetime

import requests
from sqlalchemy import create_engine, text
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("collector")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def fetch_raw_results(election_id: int) -> list[dict]:
    """
    JEDINA funkcija koju treba prilagoditi stvarnom izvoru.

    Mora vratiti listu rečnika u obliku:
    [
        {
            "rik_station_code": "01-001-0001",
            "party_ballot_number": 1,
            "votes": 234,
            "valid_ballots": 480,
            "invalid_ballots": 12,
            "total_voted": 492,
            "is_processed": True,
        },
        ...
    ]

    Primer skeletona za JSON API (prilagoditi URL i strukturu odgovora
    kada se utvrdi stvarni format):

        resp = requests.get(f"https://rik.parlament.gov.rs/api/results/{election_id}", timeout=15)
        resp.raise_for_status()
        return resp.json()["stations"]

    Primer skeletona za HTML scraping (ako nema API-ja):

        from bs4 import BeautifulSoup
        resp = requests.get("https://rik.parlament.gov.rs/rezultati", timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        # ... parsiranje tabele ...
    """
    raise NotImplementedError(
        "Podesiti stvarni izvor podataka pre prve live upotrebe. "
        "Do tada koristiti seed skriptu sa istorijskim/mock podacima."
    )


def validate(raw_results: list[dict]) -> list[dict]:
    """Osnovna sanity provera pre upisa — odbaci nekonzistentne redove."""
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
    updated = 0
    with engine.begin() as conn:
        for row in rows:
            station = conn.execute(
                text("SELECT id FROM polling_stations WHERE rik_code = :code"),
                {"code": row["rik_station_code"]},
            ).fetchone()
            if not station:
                log.warning("Nepoznato biračko mesto: %s", row["rik_station_code"])
                continue
            party = conn.execute(
                text("SELECT id FROM parties WHERE election_id = :eid AND ballot_number = :n"),
                {"eid": election_id, "n": row["party_ballot_number"]},
            ).fetchone()
            if not party:
                log.warning("Nepoznata lista broj %s", row["party_ballot_number"])
                continue

            conn.execute(
                text(
                    """
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
                    """
                ),
                {
                    "eid": election_id,
                    "sid": station.id,
                    "pid": party.id,
                    "votes": row["votes"],
                    "valid": row.get("valid_ballots"),
                    "invalid": row.get("invalid_ballots"),
                    "total": row.get("total_voted"),
                    "processed": row.get("is_processed", False),
                    "now": datetime.utcnow(),
                },
            )
            updated += 1
    return updated


def log_ingestion(election_id: int, source: str, stations_updated: int, success: bool, error: str = None):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ingestion_log (election_id, source, stations_updated, success, error_message)
                VALUES (:eid, :source, :count, :success, :error)
                """
            ),
            {"eid": election_id, "source": source, "count": stations_updated, "success": success, "error": error},
        )


def run_once(election_id: int):
    try:
        raw = fetch_raw_results(election_id)
        clean = validate(raw)
        count = upsert_results(election_id, clean)
        log_ingestion(election_id, "rik_api", count, True)
        log.info("Ažurirano %d biračkih mesta", count)
    except NotImplementedError as e:
        log.error(str(e))
    except Exception as e:
        log.exception("Greška pri povlačenju podataka")
        log_ingestion(election_id, "rik_api", 0, False, str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--election-id", type=int, required=True)
    parser.add_argument("--interval", type=int, default=45, help="Sekunde između povlačenja (30-60 preporučeno)")
    parser.add_argument("--once", action="store_true", help="Pokreni samo jednom, bez petlje")
    args = parser.parse_args()

    if args.once:
        run_once(args.election_id)
        return

    log.info("Collector pokrenut, interval %ds", args.interval)
    while True:
        run_once(args.election_id)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
