#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild 2026 party list from scratch with correct 19 lists.
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

# Delete all parties for election 2026 and re-insert correct list
cur.execute("DELETE FROM parties WHERE election_id=3")
print("Deleted all parties for election 2026")

# Correct 2026 RIK ballot lists (19 lists after withdrawal of #9, added Albanska koalicija and Majka Srbija-Gruda)
CORRECT_LISTS = [
    (1, False, "АЛЕКСАНДАР ВУЧИЋ – УЈЕДИЊЕНА СРБИЈА", "#0E4DA4"),
    (2, False, "ИВИЦА ДАЧИЋ – ФАКТОР СТАБИЛНОСТИ (SPS)", "#ED1C24"),
    (3, False, "СТУДЕНТСКА ЛИСТА – СТУДЕНТИ ПОБЕЂУЈУ", "#800020"),
    (4, True, "РАСИМ ЉАЈИЋ – ЉУДСКИ (СДП–ЦДП)", "#F26522"),
    (5, True, "VAJDASÁGI MAGYAR SZÖVETSÉG – DR. PÁSZTOR BÁLINT", "#00A651"),
    (6, True, "USAME ZUKORLIĆ (SPP) ПОКРЕТ ЗА УЈЕДИЊЕЊЕ", "#006B3F"),
    (7, True, "РУСКА СТРАНКА – СРБИЈА У БРИКСУ – СЛОБОДАН НИКОЛИЋ", "#4682B4"),
    (8, False, "АУТЕНТИЧНА ДЕСНИЦА – ДР МИЛОШ ЈОВАНОВИЋ (НОВИ ДСС...)", "#1F3A5F"),
    (9, False, "ЕВРОПСКА СРБИЈА – МАРИНИКА ТЕПИЋ – ЗДРАВКО ПОНОШ", "#2471A3"),
    (10, True, "СДА САНЏАКА – ЧУВАРИ САНЏАКА", "#2E8B57"),
    (11, False, "БОГОЉУБ КАРИЋ – ПОКРЕТ СНАГЕ СРБИЈЕ – БК", "#457B9D"),
    (12, False, "ГРУПА ГРАЂАНА ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ", "#8E44AD"),
    (13, False, "ЛИБЕРАЛНО ЗЕЛЕНА СТРАНКА – ЗА СЛОБОДНУ И ЧИСТИЈУ СРБИЈУ", "#1B8C4A"),
    (14, False, "БИРАМ ПРАВДУ – БИРАМ БУДУЋНОСТ – КОАЛИЦИЈА СНАГА...", "#457B9D"),
    (15, True, "СТРАНКА РУСКО-СРПСКОГ ЈЕДИНСТВА – РУСИ И СРБИ БРАЋА", "#4682B4"),
    (16, False, "ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ", "#8E44AD"),
    (17, False, "ВЛАДИМИР ГАЈИЋ – АЛТЕРНАТИВА ЗА СРБИЈУ – НАРОДНА...", "#4A7FB5"),
    (18, True, "АЛБАНСКА КОАЛИЦИЈА", "#2E8B57"),
    (19, True, "МАЈКА СРБИЈА – ГРУДА", "#8E44AD"),
]

# Note: Minority parties at BN: 4, 5, 6, 7, 10, 15, 18, 19

print("Inserting 19 correct party lists...")
for bn, is_minority, name, color in CORRECT_LISTS:
    cur.execute("""
        INSERT INTO parties (election_id, name, short_name, ballot_number, color_hex, is_minority)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (3, name, name[:50], bn, color, bn in {4, 5, 6, 7, 10, 15, 18, 19}))
    try:
        print(f"  Inserted BN={bn}: {name[:60]}")
    except UnicodeEncodeError:
        print(f"  Inserted BN={bn}: {name[:60].encode('ascii','replace').decode()}")

# Verify
cur.execute("SELECT ballot_number, is_minority, name FROM parties WHERE election_id=3 ORDER BY ballot_number")
final = cur.fetchall()
print("\n=== FINAL PARTY LIST ===")
for r in final:
    try:
        print(f"  BN={r[0]:2d} MIN={r[1]} | {r[2][:80]}")
    except UnicodeEncodeError:
        print(f"  BN={r[0]:2d} MIN={r[1]} | {r[2][:80].encode('ascii','replace').decode()}")

print(f"\nTotal: {len(final)} lists")
c.close()
print("\nDone!")