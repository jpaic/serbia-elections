#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Faza A: Ispravka redosleda lista 2026 prema RIK konačnom listiću.
Dodjela ballot_number na osnovu ID-jeva iz baze.
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
load_dotenv()

# Mapiranje: database ID -> (ballot_number, is_minority, opis)
# Na osnovu inspekcije baze (check_db.py) i RIK konačnog redosleda
FIX_MAP = {
    333: (1,  False, "Aleksandar Vučić – Ujedinjena Srbija"),
    332: (2,  False, "Ivica Dačić – Faktor stabilnosti (SPS)"),
    331: (3,  False, "Studentska lista – Studenti pobeđuju"),
    330: (4,  True,  "Rasim Ljajić – Ljudski (SDP–CDP)"),
    329: (5,  True,  "Vajdasági Magyar Szövetség – dr Pásztor Bálint"),
    334: (6,  True,  "Usame Zukorlić (SPP) Pokret za ujedinjenje"),
    335: (7,  True,  "Ruska stranka – Srbija u BRIKS-u – Slobodan Nikolić"),
    336: (8,  False, "Autentična desnica – dr Miloš Jovanović (Novi DSS…)"),  # from BN=18
    337: (9,  False, "Izbor naroda – Miroslav Miki Aleksić – Miloš Parandilović"),
    338: (10, False, "Evropska Srbija – Marinika Tepić – Zdravko Ponoš"),
    339: (11, True,  "SDA Sandžaka – Čuvari Sandžaka"),
    340: (12, False, "Bogoljub Karić – Pokret snaga Srbije – BK"),
    341: (13, False, "Grupa građana Ćale ovo je za tebe – Petar Đurić – Premijer Srbije"),
    342: (14, False, "Liberalno zelena stranka – Za slobodnu i čistiju Srbiju"),
    343: (15, False, "Biram pravdu – Biram budućnost – Koalicija snaga…"),
    344: (16, True,  "Stranka rusko-srpskog jedinstva – Rusi i Srbi braća"),
    345: (17, False, "Ćale ovo je za tebe – Petar Đurić – Premijer Srbije"),
    346: (18, False, "Vladimir Gajić – Alternativa za Srbiju – Narodna…"),
}

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

    # Ažuriraj svaku listu
    for pid, (bn, minority, desc) in FIX_MAP.items():
        cur.execute(
            "UPDATE parties SET ballot_number=%s, is_minority=%s WHERE id=%s AND election_id=%s",
            (bn, minority, pid, eid)
        )
        if cur.rowcount == 1:
            try:
                print(f"  OK ID={pid:3d} -> BN={bn:2d} MIN={str(minority):5s} | {desc}")
            except UnicodeEncodeError:
                print(f"  OK ID={pid:3d} -> BN={bn:2d} MIN={str(minority):5s} | {desc.encode('ascii','replace').decode()}")
        else:
            print(f"  !! ID={pid:3d} NIJE AZURIRANA (rowcount={cur.rowcount})")

    # Provera
    cur.execute("SELECT id, ballot_number, is_minority, short_name FROM parties WHERE election_id=%s ORDER BY ballot_number", (eid,))
    print("\n--- STANJE POSLE AZURIRANJA ---")
    for r in cur.fetchall():
        try:
            print(f"  ID={r[0]} BN={r[1]} MIN={r[2]} | {r[3]}")
        except UnicodeEncodeError:
            print(f"  ID={r[0]} BN={r[1]} MIN={r[2]} | {r[3].encode('ascii','replace').decode()}")

    # Proveri duplikate
    cur.execute("SELECT ballot_number, COUNT(*) FROM parties WHERE election_id=%s GROUP BY ballot_number HAVING COUNT(*) > 1", (eid,))
    dupes = cur.fetchall()
    if dupes:
        print("\n!!! DUPLIKATI BALLOT_NUMBER:")
        for bn, cnt in dupes:
            print(f"  BN={bn}: {cnt} lista")
    else:
        print("\nNema duplikata ballot_number.")

    # Proveri pokrivanje 1-18
    cur.execute("SELECT ballot_number FROM parties WHERE election_id=%s", (eid,))
    bns = {r[0] for r in cur.fetchall()}
    missing = [i for i in range(1, 19) if i not in bns]
    if missing:
        print(f"\nNEDOSTAJUCI BROJEVI: {missing}")
    else:
        print("\nSvi brojevi 1-18 prisutni.")

    c.close()
    print("\nGotovo.")


if __name__ == "__main__":
    main()