"""
Puni bazu mock/demo podacima da ceo pipeline (baza -> API -> frontend) radi
offline, pre nego što se poveže pravi RIK izvor. Ovo je "historical/offline
verzija" pomenuta u tački 8 plana.

Pokretanje:
    pip install sqlalchemy psycopg2-binary faker --break-system-packages
    export DATABASE_URL=postgresql://user:pass@host:5432/izbori
    python seed_demo_data.py
"""
import os
import random
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
engine = create_engine(DATABASE_URL)

# rzs_code je RIK data-id (1-na-1 sa RIK mapom); regioni su RIK nazivi (5).
# Palilula Beograd=70203 se time razlikuje od Palilule Nis (71323).
# "Nis" je ceo grad bez 1-na-1 RIK pandana (RIK ima 5 niskih opstina).
MUNICIPALITIES = [
    ("70092", "Barajevo", "Београдски регион", 27000),
    ("70254", "Čukarica", "Београдски регион", 180000),
    ("70122", "Grocka", "Београдски регион", 85000),
    ("70165", "Lazarevac", "Београдски регион", 58000),
    ("70173", "Mladenovac", "Београдски регион", 52000),
    ("70181", "Novi Beograd", "Београдски регион", 210000),
    ("70190", "Obrenovac", "Београдски регион", 72000),
    ("70203", "Palilula", "Београдски регион", 175000),
    ("70211", "Rakovica", "Београдски регион", 108000),
    ("70220", "Savski venac", "Београдски регион", 39000),
    ("70238", "Sopot", "Београдски регион", 20000),
    ("70246", "Stari grad", "Београдски регион", 48000),
    ("71293", "Surčin", "Београдски регион", 45000),
    ("70106", "Voždovac", "Београдски регион", 165000),
    ("70114", "Vračar", "Београдски регион", 56000),
    ("70157", "Zemun", "Београдски регион", 170000),
    ("70149", "Zvezdara", "Београдски регион", 172000),
    ("89010", "Novi Sad", "Регион Војводине", 340000),
    ("80314", "Pančevo", "Регион Војводине", 120000),
    ("80438", "Subotica", "Регион Војводине", 140000),
    ("80152", "Zrenjanin", "Регион Војводине", 120000),
    ("70645", "Kragujevac", "Регион Шумадије и Западне Србије", 170000),
    ("70653", "Kraljevo", "Регион Шумадије и Западне Србије", 120000),
    ("70874", "Novi Pazar", "Регион Шумадије и Западне Србије", 100000),
    ("71242", "Čačak", "Регион Шумадије и Западне Србије", 110000),
    ("00003", "Niš", "Регион Јужне и Источне Србије", 260000),
]

PARTIES = [
    ("Lista A", "A", 1, "#D85A30"),
    ("Lista B", "B", 2, "#378ADD"),
    ("Lista C", "C", 3, "#EF9F27"),
]


def run():
    with engine.begin() as conn:
        election_id = conn.execute(
            text(
                """
                INSERT INTO elections (name, election_type, election_date, status)
                VALUES ('Parlamentarni izbori 2026 (demo)', 'parliamentary', CURRENT_DATE, 'live')
                RETURNING id
                """
            )
        ).scalar()

        party_ids = []
        for name, short, num, color in PARTIES:
            pid = conn.execute(
                text(
                    """
                    INSERT INTO parties (election_id, name, short_name, ballot_number, color_hex)
                    VALUES (:eid, :name, :short, :num, :color) RETURNING id
                    """
                ),
                {"eid": election_id, "name": name, "short": short, "num": num, "color": color},
            ).scalar()
            party_ids.append(pid)

        for code, name, region, population in MUNICIPALITIES:
            registered = int(population * 0.75)
            mid = conn.execute(
                text(
                    """
                    INSERT INTO municipalities (rzs_code, name, region, population, registered_voters)
                    VALUES (:code, :name, :region, :pop, :reg) RETURNING id
                    """
                ),
                {"code": code, "name": name, "region": region, "pop": population, "reg": registered},
            ).scalar()

            num_stations = max(3, population // 3000)
            for s in range(num_stations):
                rik_code = f"{code}-{s+1:04d}"
                station_voters = registered // num_stations
                sid = conn.execute(
                    text(
                        """
                        INSERT INTO polling_stations (municipality_id, rik_code, name, registered_voters)
                        VALUES (:mid, :rik, :name, :voters) RETURNING id
                        """
                    ),
                    {"mid": mid, "rik": rik_code, "name": f"{name} - biračko mesto {s+1}", "voters": station_voters},
                ).scalar()

                is_processed = random.random() < 0.6
                if is_processed:
                    turnout = random.uniform(0.4, 0.65)
                    total_voted = int(station_voters * turnout)
                    invalid = int(total_voted * random.uniform(0.01, 0.03))
                    valid = total_voted - invalid
                    shares = [random.random() for _ in party_ids]
                    total_share = sum(shares)
                    for pid, share in zip(party_ids, shares):
                        votes = int(valid * share / total_share)
                        conn.execute(
                            text(
                                """
                                INSERT INTO results
                                    (election_id, polling_station_id, party_id, votes,
                                     valid_ballots, invalid_ballots, total_voted, is_processed)
                                VALUES (:eid, :sid, :pid, :votes, :valid, :invalid, :total, true)
                                """
                            ),
                            {
                                "eid": election_id,
                                "sid": sid,
                                "pid": pid,
                                "votes": votes,
                                "valid": valid,
                                "invalid": invalid,
                                "total": total_voted,
                            },
                        )

    print(f"Готово. election_id = {election_id}")


if __name__ == "__main__":
    run()
