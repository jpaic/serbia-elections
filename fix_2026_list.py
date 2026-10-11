#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix 2026 party list: remove withdrawn list #9 (Izbor naroda), 
remove duplicate Ćale entry, and fix minority flags.
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")

DATABASE_URL = os.environ.get("DATABASE_URL")
c = psycopg2.connect(DATABASE_URL)
c.autocommit = True
cur = c.cursor()

# Get current parties
cur.execute("SELECT id, ballot_number, short_name FROM parties WHERE election_id=3 ORDER BY ballot_number")
current = cur.fetchall()
print("Current parties:")
for r in current:
    try:
        print(f"  BN={r[1]} ID={r[0]} | {r[2][:80]}")
    except UnicodeEncodeError:
        print(f"  BN={r[1]} ID={r[0]} | {r[2][:80].encode('ascii','replace').decode()}")

# The correct 2026 RIK ballot lists (after withdrawal of #9 Izbor naroda)
# Official RIK ballot lists for 2026 parliamentary elections (17 lists total)
CORRECT_LISTS = [
    (1, False, "АЛЕКСАНДАР ВУЧИЋ – УЈЕДИЊЕНА СРБИЈА"),
    (2, False, "ИВИЦА ДАЧИЋ – ФАКТОР СТАБИЛНОСТИ (SPS)"),
    (3, False, "СТУДЕНТСКА ЛИСТА – СТУДЕНТИ ПОБЕЂУЈУ"),
    (4, True, "РАСИМ ЉАЈИЋ – ЉУДСКИ (СДП–ЦДП)"),  # minority
    (5, True, "VAJDASÁGI MAGYAR SZÖVETSÉG – DR. PÁSZTOR BÁLINT"),  # SVM - minority
    (6, True, "USAME ZUKORLIĆ (SPP) ПОКРЕТ ЗА УЈЕДИЊЕЊЕ"),  # SPP - minority
    (7, True, "РУСКА СТРАНКА – СРБИЈА У БРИКСУ – СЛОБОДАН НИКОЛИЋ"),  # minority
    (8, False, "АУТЕНТИЧНА ДЕСНИЦА – ДР МИЛОШ ЈОВАНОВИЋ (НОВИ ДСС...)"),
    (9, False, "ЕВРОПСКА СРБИЈА – МАРИНИКА ТЕПИЋ – ЗДРАВКО ПОНОШ"),  # was 10
    (10, True, "СДА САНЏАКА – ЧУВАРИ САНЏАКА"),  # SDA - minority, was 11
    (11, False, "БОГОЉУБ КАРИЋ – ПОКРЕТ СНАГЕ СРБИЈЕ – БК"),  # was 12
    (12, False, "ГРУПА ГРАЂАНА ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ"),  # was 13
    (13, False, "ЛИБЕРАЛНО ЗЕЛЕНА СТРАНКА – ЗА СЛОБОДНУ И ЧИСТИЈУ СРБИЈУ"),  # was 14
    (14, False, "БИРАМ ПРАВДУ – БИРАМ БУДУЋНОСТ – КОАЛИЦИЈА СНАГА..."),  # was 15
    (15, True, "СТРАНКА РУСКО-СРПСКОГ ЈЕДИНСТВА – РУСИ И СРБИ БРАЋА"),  # minority, was 16
    (16, False, "ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ"),  # was 17 (different from 13)
    (17, False, "ВЛАДИМИР ГАЈИЋ – АЛТЕРНАТИВА ЗА СРБИЈУ – НАРОДНА..."),  # was 18
]

print("\nApplying corrections...")

# First, delete the withdrawn list #9 (Izbor naroda)
cur.execute("DELETE FROM parties WHERE election_id=3 AND ballot_number=9")
print("Deleted withdrawn list #9 (Izbor naroda)")

# Also remove duplicate Ćale list (the second one, originally BN=17, now BN=16 after renumbering)
# The duplicate is "ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ" (shorter name)
# Keep "ГРУПА ГРАЂАНА ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ" (longer name)
# Find and delete the duplicate
cur.execute("""
    DELETE FROM parties 
    WHERE election_id=3 
    AND name LIKE '%ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ%'
    AND name NOT LIKE '%ГРУПА ГРАЂАНА%'
""")
print("Deleted duplicate Calist (shorter name variant)")

# Get current parties again after deletion
cur.execute("SELECT id, ballot_number, short_name FROM parties WHERE election_id=3 ORDER BY ballot_number")
current = cur.fetchall()
print("\nCurrent parties after deleting #9:")
for r in current:
    try:
        print(f"  ID={r[0]} BN={r[1]} | {r[2][:80]}")
    except UnicodeEncodeError:
        print(f"  ID={r[0]} BN={r[1]} | {r[2][:80].encode('ascii','replace').decode()}")

# Build mapping of current ballot numbers to correct ones
# After deleting #9: current BNs are [1,2,3,4,5,6,7,8,10,11,12,13,14,15,16,17,18]
# Should become: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]

bn_mapping = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8,
    10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14, 16: 15, 18: 17
}

# Also update minority flags based on correct list (after renumbering)
# Minority parties at new BNs: 4=Ljajić, 5=SVM, 6=SPP, 7=Russian, 10=SDA, 15=Rusko-srpsko
minority_bns = {4, 5, 6, 7, 10, 15}

print("\nApplying ballot number corrections...")
for old_bn, new_bn in bn_mapping.items():
    cur.execute("UPDATE parties SET ballot_number=%s WHERE election_id=3 AND ballot_number=%s", (new_bn, old_bn))
    if cur.rowcount:
        print(f"  BN {old_bn} -> {new_bn}")

# Also update minority flags
print("\nUpdating minority flags...")
cur.execute("SELECT id, ballot_number, short_name FROM parties WHERE election_id=3 ORDER BY ballot_number")
parties = cur.fetchall()
minority_bns = {4, 5, 6, 7, 10, 15}  # correct BNs that are minority
for pid, bn, name in parties:
    is_minority = bn in minority_bns
    cur.execute("UPDATE parties SET is_minority=%s WHERE id=%s", (is_minority, pid))
    try:
        print(f"  BN={bn:2d} MIN={is_minority} | {name[:60]}")
    except UnicodeEncodeError:
        print(f"  BN={bn:2d} MIN={is_minority} | {name[:60].encode('ascii','replace').decode()}")

# Update names to match official RIK names
print("\nUpdating names to match official RIK list...")
name_updates = {
    1: "АЛЕКСАНДАР ВУЧИЋ – УЈЕДИЊЕНА СРБИЈА",
    2: "ИВИЦА ДАЧИЋ – ФАКТОР СТАБИЛНОСТИ (SPS)",
    3: "СТУДЕНТСКА ЛИСТА – СТУДЕНТИ ПОБЕЂУЈУ",
    4: "РАСИМ ЉАЈИЋ – ЉУДСКИ (СДП–ЦДП)",
    5: "VAJDASÁGI MAGYAR SZÖVETSÉG – DR. PÁSZTOR BÁLINT",
    6: "USAME ZUKORLIĆ (SPP) ПОКРЕТ ЗА УЈЕДИЊЕЊЕ",
    7: "РУСКА СТРАНКА – СРБИЈА У БРИКСУ – СЛОБОДАН НИКОЛИЋ",
    8: "АУТЕНТИЧНА ДЕСНИЦА – ДР МИЛОШ ЈОВАНОВИЋ (НОВИ ДСС...)",
    9: "ЕВРОПСКА СРБИЈА – МАРИНИКА ТЕПИЋ – ЗДРАВКО ПОНОШ",
    10: "СДА САНЏАКА – ЧУВАРИ САНЏАКА",
    11: "БОГОЉУБ КАРИЋ – ПОКРЕТ СНАГЕ СРБИЈЕ – БК",
    12: "ГРУПА ГРАЂАНА ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ",
    13: "ЛИБЕРАЛНО ЗЕЛЕНА СТРАНКА – ЗА СЛОБОДНУ И ЧИСТИЈУ СРБИЈУ",
    14: "БИРАМ ПРАВДУ – БИРАМ БУДУЋНОСТ – КОАЛИЦИЈА СНАГА...",
    15: "СТРАНКА РУСКО-СРПСКОГ ЈЕДИНСТВА – РУСИ И СРБИ БРАЋА",
    16: "ЋАЛЕ ОВО ЈЕ ЗА ТЕБЕ – ПЕТАР ЂУРИЋ – ПРЕМИЈЕР СРБИЈЕ",
    17: "ВЛАДИМИР ГАЈИЋ – АЛТЕРНАТИВА ЗА СРБИЈУ – НАРОДНА...",
}

for bn, name in name_updates.items():
    cur.execute("UPDATE parties SET name=%s WHERE election_id=3 AND ballot_number=%s", (name, bn))
    if cur.rowcount:
        try:
            print(f"  Updated BN={bn}: {name[:60]}")
        except UnicodeEncodeError:
            print(f"  Updated BN={bn}: {name[:60].encode('ascii','replace').decode()}")

# Verify final state
cur.execute("SELECT ballot_number, is_minority, short_name FROM parties WHERE election_id=3 ORDER BY ballot_number")
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