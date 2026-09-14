"""
Bootstrap skripta — jednokratno po izbornom krugu puni:
  municipalities, polling_stations, election_station_codes i parties.

Koristi rik_client.py (cascading API). Pokretanje:

    pip install requests beautifulsoup4 sqlalchemy psycopg[binary] --break-system-packages
    export DATABASE_URL=postgresql://user:pass@host:5432/izbori
    python bootstrap.py --election-type 2 --election-round 341140 --election-date 2023-12-17
    python bootstrap.py --election-type 2 --election-round 680072 --election-date 2026-10-25

Ako izbori već postoje u bazi (po rik_round), samo dopunjuje nedostajuće opštine/mesta/mapu.
"""
import argparse
import os
import logging
import re
from datetime import datetime

from sqlalchemy import create_engine, text

from rik_client import create_session, get_regions, get_municipalities, get_election_stations, get_results_raw, parse_table_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bootstrap")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

ELECTION_TYPE_MAP = {
    1: ("presidential", "Председнички"),
    2: ("parliamentary", "Парламентарни"),
    3: ("local", "Локални"),
    4: ("provincial", "Покрајински"),
}

# Region id -> naziv za mapu (fallback ako RIK ne vrati region string kasnije)
# Koristimo tačno kako RIK vraća za kasnije slaganje sa geojson-om preko m.region
REGION_NAMES = {
    1: "Београдски регион",
    2: "Регион Војводине",
    3: "Регион Шумадије и Западне Србије",
    4: "Регион Јужне и Источне Србије",
    5: "Регион Косово и Метохија",
    100: "Заводи за извршење кривичних санкција",
    101: "Иностранство",
}


def ensure_election(conn, rik_type: int, rik_round: int, election_date: str, name: str = None):
    existing = conn.execute(text("SELECT id FROM elections WHERE rik_round = :r"), {"r": rik_round}).fetchone()
    if existing:
        log.info("Izbori rik_round=%s već postoje id=%s", rik_round, existing.id)
        return existing.id

    type_str, prefix = ELECTION_TYPE_MAP.get(rik_type, ("parliamentary", "Избори"))
    final_name = name or f"{prefix} {election_date}"
    # election_type kolona je VARCHAR(50) - koristimo engleski tip
    eid = conn.execute(text("""
        INSERT INTO elections (name, election_type, election_date, status, rik_type, rik_round)
        VALUES (:name, :etype, :edate, :status, :rtype, :rround)
        RETURNING id
    """), {
        "name": final_name,
        "etype": type_str,
        "edate": election_date,
        "status": "upcoming",
        "rtype": rik_type,
        "rround": rik_round,
    }).scalar()
    log.info("Kreirani izbori id=%s name=%s rik=%s/%s", eid, final_name, rik_type, rik_round)
    return eid


def ensure_municipality(conn, region_name: str, mun_value: int, mun_data_id: str, mun_name: str):
    # municipalities.rzs_code koristimo za RIK data-id (70157...), UNIQUE
    # Ako data_id nedostaje, koristimo fallback value
    rzs_code = str(mun_data_id or f"rik-{mun_value}")
    existing = conn.execute(text("SELECT id FROM municipalities WHERE rzs_code = :c"), {"c": rzs_code}).fetchone()
    if existing:
        return existing.id
    # pokušaj po imenu+regionu kao fallback
    by_name = conn.execute(text("SELECT id FROM municipalities WHERE name = :n AND region = :r"), {"n": mun_name, "r": region_name}).fetchone()
    if by_name:
        # dopuni rzs_code
        conn.execute(text("UPDATE municipalities SET rzs_code = :c WHERE id = :id"), {"c": rzs_code, "id": by_name.id})
        return by_name.id

    mid = conn.execute(text("""
        INSERT INTO municipalities (rzs_code, name, region)
        VALUES (:c, :n, :r) RETURNING id
    """), {"c": rzs_code, "n": mun_name, "r": region_name}).scalar()
    log.info("  + opština %s (%s) region=%s", mun_name, rzs_code, region_name)
    return mid


def ensure_polling_station(conn, municipality_id: int, station_rik_id: int, station_full_name: str):
    # station_full_name: "1 - ОШ \"СВЕТОЗАР МИЛЕТИЋ\""
    # Koristimo full name kao UNIQUE ključ (municipality_id, name)
    existing = conn.execute(text(
        "SELECT id FROM polling_stations WHERE municipality_id = :mid AND name = :name"
    ), {"mid": municipality_id, "name": station_full_name}).fetchone()
    if existing:
        return existing.id

    sid = conn.execute(text("""
        INSERT INTO polling_stations (municipality_id, name, rik_code)
        VALUES (:mid, :name, :code) RETURNING id
    """), {"mid": municipality_id, "name": station_full_name, "code": str(station_rik_id)}).scalar()
    return sid


def ensure_party(conn, election_id: int, ballot_number: int, list_name: str):
    existing = conn.execute(text(
        "SELECT id FROM parties WHERE election_id = :eid AND ballot_number = :bn"
    ), {"eid": election_id, "bn": ballot_number}).fetchone()
    if existing:
        return existing.id
    # short_name = skraćeno, npr. "1. SNS"
    short = re.sub(r"^\s*\d+\.\s*", "", list_name).strip()[:50] or f"Lista {ballot_number}"
    pid = conn.execute(text("""
        INSERT INTO parties (election_id, name, short_name, ballot_number)
        VALUES (:eid, :name, :short, :bn) RETURNING id
    """), {"eid": election_id, "name": list_name.strip(), "short": short, "bn": ballot_number}).scalar()
    log.info("  + lista %s: %s", ballot_number, short[:60])
    return pid


def main():
    ap = argparse.ArgumentParser(description="Bootstrap RIK municipalities/stations/parties za jedan izborni krug")
    ap.add_argument("--election-type", type=int, required=True, help="RIK election_type (2=parlamentarni, 3=lokalni)")
    ap.add_argument("--election-round", type=int, required=True, help="RIK election_round id (npr. 341140)")
    ap.add_argument("--election-date", type=str, required=True, help="YYYY-MM-DD za elections.election_date")
    ap.add_argument("--election-name", type=str, default=None, help="Opcioni naziv izbora")
    ap.add_argument("--delay", type=float, default=0.35, help="Sekunde između RIK poziva")
    args = ap.parse_args()

    session = create_session()

    # 0) izbori + liste (brzo, jedna transakcija)
    with engine.begin() as conn:
        election_id = ensure_election(conn, args.election_type, args.election_round, args.election_date, args.election_name)

    # 1) regions (samo čitanje sa RIK-a, bez baze)
    regions_resp = get_regions(session, args.election_type, args.election_round)
    regions = regions_resp.get("regions") or {}
    if not regions:
        log.error("get-regions vratio prazno: %s", regions_resp)
        return
    log.info("Regioni: %s", ", ".join(f"{k}={v}" for k, v in regions.items()))

    # 2) parties — iz nacionalnog get_results
    with engine.begin() as conn:
        raw_national = get_results_raw(session, args.election_type, args.election_round)
        table = parse_table_data(raw_national)
        if table:
            for row in table:
                ensure_party(conn, election_id, row["ballot_number"], row["name"])
            log.info("Upisano %d lista za izbore id=%s", len(table), election_id)
        else:
            log.warning("Nema table_data za parties (možda izbori bez rezultata kao 2026)")

    # 3) municipalities + stations + election_station_codes
    #    KOMIT PO OPŠTINI: prekid ne briše urađeno, ponovno pokretanje nastavlja (idempotentno).
    total_stations = 0
    done_muns = 0
    for region_id_str, region_name in regions.items():
        try:
            region_id = int(region_id_str)
        except ValueError:
            continue
        muns = get_municipalities(session, args.election_type, args.election_round, region_id)
        log.info("Region %s (%s): %d opština", region_id, region_name, len(muns))
        for mun in muns:
            mun_value = mun["value"]
            mun_data_id = mun["data_id"]
            mun_name = mun["name"]
            # RESUME: ako opština već ima mapirana mesta za ovaj krug, preskoči fetch
            with engine.connect() as _c:
                _mid = _c.execute(text(
                    "SELECT id FROM municipalities WHERE rzs_code = :c"
                ), {"c": str(mun_data_id or f"rik-{mun_value}")}).fetchone()
                if _mid:
                    _n = _c.execute(text(
                        """SELECT COUNT(*) FROM election_station_codes esc
                           JOIN polling_stations ps ON ps.id = esc.polling_station_id
                           WHERE esc.election_id = :eid AND ps.municipality_id = :mid"""
                    ), {"eid": election_id, "mid": _mid.id}).scalar()
                    if (_n or 0) > 0:
                        total_stations += int(_n)
                        done_muns += 1
                        continue
            try:
                stations = get_election_stations(session, args.election_type, args.election_round, region_id, mun_value)
            except Exception as e:
                log.warning("get-election-stations greška za %s: %s (preskačem)", mun_name, e)
                continue
            rik_ids = []
            for rik_sid_str in stations:
                try:
                    rik_ids.append(int(rik_sid_str))
                except ValueError:
                    continue

            with engine.begin() as conn:
                municipality_id = ensure_municipality(conn, region_name, mun_value, mun_data_id, mun_name)
                if stations:
                    # grupni upis mesta (1 roundtrip), pa grupni upis kodova (1 roundtrip)
                    conn.execute(text("""
                        INSERT INTO polling_stations (municipality_id, name, rik_code)
                        VALUES (:mid, :name, :code)
                        ON CONFLICT (municipality_id, name) DO NOTHING
                    """), [
                        {"mid": municipality_id, "name": full_name, "code": str(rik_sid)}
                        for rik_sid, full_name in
                        ((int(k), v) for k, v in stations.items() if k.lstrip("-").isdigit())
                    ])
                    id_rows = conn.execute(text(
                        "SELECT id, rik_code FROM polling_stations WHERE municipality_id = :mid"
                    ), {"mid": municipality_id}).fetchall()
                    # mapiraj po rik_code (stabilno za ovaj krug); fallback po imenu
                    by_code = {r.rik_code: r.id for r in id_rows}
                    by_name = dict(conn.execute(text(
                        "SELECT name, id FROM polling_stations WHERE municipality_id = :mid"
                    ), {"mid": municipality_id}).fetchall())
                    code_params = []
                    for rik_sid_str, full_name in stations.items():
                        sid = by_code.get(str(rik_sid_str)) or by_name.get(full_name)
                        if sid is None:
                            continue
                        try:
                            code_params.append({"eid": election_id, "psid": int(sid), "rik": int(rik_sid_str)})
                        except ValueError:
                            continue
                    if code_params:
                        conn.execute(text("""
                            INSERT INTO election_station_codes (election_id, polling_station_id, rik_station_id)
                            VALUES (:eid, :psid, :rik)
                            ON CONFLICT (election_id, polling_station_id)
                            DO UPDATE SET rik_station_id = EXCLUDED.rik_station_id
                        """), code_params)
            total_stations += len(rik_ids)
            done_muns += 1
            if done_muns % 20 == 0:
                log.info("Progres: %d opština, %d mesta...", done_muns, total_stations)

    log.info("Gotovo. election_id=%s ukupno mapirano biračkih mesta: %s", election_id, total_stations)
    # prebaci status ako su izbori u prošlosti
    try:
        ed = datetime.strptime(args.election_date, "%Y-%m-%d").date()
        from datetime import date
        if ed < date.today():
            with engine.begin() as conn:
                conn.execute(text("UPDATE elections SET status='closed' WHERE id=:id AND status='upcoming'"), {"id": election_id})
    except Exception:
        pass


if __name__ == "__main__":
    main()
