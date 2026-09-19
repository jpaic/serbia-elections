# -*- coding: utf-8 -*-
"""Upis proglasenih lista 2026 (election id=3) iz raw/2026-dokumenti.json.
Ponovljivo: nove liste se dodaju, postojece se azuriraju po imenu.
Redni brojevi su privremeni (po redosledu proglasenja) do zreba RIK-a.
"""
import json
import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv()

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
PALETTE = ["#e63946", "#457b9d", "#7c3aed", "#78716c", "#f59e0b", "#0ea5e9",
           "#22c55e", "#a855f7", "#14b8a6", "#94a3b8", "#3b82d6", "#f97316",
           "#84cc16", "#eab308", "#64748b", "#ef4444", "#8b5cf6", "#06b6d4"]

# kljucna rec -> (boja, manjina) — redosled osetljiv, prva pogodjena pobeđuje
COLOR_RULES = [
    ("ВУЧИЋ", "#0E4DA4", False),
    ("VUČIĆ", "#0E4DA4", False),
    ("ДАЧИЋ", "#ED1C24", False),
    ("DAČIĆ", "#ED1C24", False),
    ("МАЂАР", "#00A651", True),
    ("MAGYAR", "#00A651", True),
    ("PÁSZTOR", "#00A651", True),
    ("ЉАЈИЋ", "#F26522", True),
    ("LJAJIĆ", "#F26522", True),
    ("СТУДЕНТ", "#800020", False),
    ("STUDENT", "#800020", False),
    ("ЗУКОРЛИ", "#006B3F", True),
    ("ZUKORLI", "#006B3F", True),
    ("СПП", "#006B3F", True),
    ("ШАПИЋ", "#4A90D9", False),
    ("ŠAPIĆ", "#4A90D9", False),
    ("ШЕШЕЉ", "#0B2A5B", False),
    ("ŠEŠELJ", "#0B2A5B", False),
    ("ДВЕРИ", "#B02A30", False),
    ("DVERI", "#B02A30", False),
    ("СДА", "#2E8B57", True),
    ("ЗАВЕТНИ", "#7B1E1E", False),
    ("ZAVETNI", "#7B1E1E", False),
    ("АУТЕНТИЧНА", "#1F3A5F", False),
    ("НАДА", "#1F3A5F", False),
    ("NADA", "#1F3A5F", False),
    ("АЛЕКСИЋ", "#2471A3", False),
    ("ALEKSIĆ", "#2471A3", False),
    ("ПАРАНДИЛОВИЋ", "#2471A3", False),
    ("ЕКОЛОШКИ УСТАНАК", "#1B8C4A", False),
    ("МОРАМО", "#1B8C4A", False),
    ("MORAMO", "#1B8C4A", False),
    ("ДОСТА ЈЕ БИЛО", "#F26522", False),
    ("РУСКА", "#4682B4", True),
    ("БРИКС", "#4682B4", True),
    ("NARODNA", "#1B75BC", False),
    ("НАРОДНА СТРАНКА", "#1B75BC", False),
]


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().upper()


def short_name(name):
    s = re.sub(r"^\s*\d+\.\s*", "", name).strip()
    return s[:50] or name.strip()[:50]


def _canonicalize_jovanovic(name, izborna_map):
    # RIK proglašenje za NADA nema prefiks "АУТЕНТИЧНА ДЕСНИЦА", dok zvanična izborna lista (8.ИЗБОРНА ЛИСТА...) ima.
    # Da ne dupliramo, mapiraj proglašeni oblik na zvanični.
    if "ЈОВАНОВИЋ" in name and "НАДА" in name and "АУТЕНТИЧНА" not in name:
        for iname in izborna_map.values():
            if "ЈОВАНОВИЋ" in iname and "НАДА" in iname and "АУТЕНТИЧНА" in iname:
                return iname
        # fallback konstrukcija (isti kao RIK izborna lista 8.)
        return "АУТЕНТИЧНА ДЕСНИЦА – ДР МИЛОШ ЈОВАНОВИЋ (НОВИ ДСС – МОНАРХИСТИ – СРПСКА КОАЛИЦИЈА НАДА – НАЦИОНАЛНО ДЕМОКРАТСКА АЛТЕРНАТИВА – НОВА ДЕМОКРАТСКА СТРАНКА СРБИЈЕ – ПОКРЕТ ЗА КРАЉЕВИНУ СРБИЈУ) – ОДВАЖНО СРПСКИ!"
    return name


def main():
    docs = json.load(open(os.path.join(RAW, "2026-dokumenti.json"), encoding="utf-8"))
    # Zvanične izborne liste (sa rednim brojem glasačkog listića) — izvor za tačan naziv
    izborna_by_ballot = {}
    for x in docs:
        dn = x.get("document_name", "")
        if "ИЗБОРНА ЛИСТА" in dn:
            m = re.match(r"^\s*(\d+)\s*\.\s*ИЗБОРНА ЛИСТА\s*(.*)", dn, re.IGNORECASE)
            if m:
                try:
                    bn = int(m.group(1))
                except ValueError:
                    continue
                name_raw = m.group(2).strip()
                # ukloni vodeći "–"/"-" ako postoji, pa normalizuj
                name_raw = re.sub(r"^[–—-]\s*", "", name_raw)
                name = norm(name_raw)
                if name:
                    izborna_by_ballot[bn] = name
    lists = []
    for x in docs:
        dn = x.get("document_name", "")
        if "ПРОГЛАШЕЊУ" in dn:
            name = norm(dn.replace("РЕШЕЊЕ О ПРОГЛАШЕЊУ ИЗБОРНЕ ЛИСТЕ", ""))
            name = _canonicalize_jovanovic(name, izborna_by_ballot)
            num = int(re.sub(r"\D", "", x.get("number", "0")) or 0)
            try:
                dt = int(str(x.get("datetime", "0")).strip())
            except ValueError:
                dt = 0
            lists.append((dt, num, name))
    # hronološki po datumu proglašenja (datetime), pa po broju dokumenta kao tie-breaker
    # ovo čuva redosled 1..7 (Vučić→Ruska) i dodaje nove na kraj (NADA-Jovanović, Narodni pokret-Aleksić)
    # naspram sortiranja samo po 'number' koje bi invertovalo redosled zbog RIK paginacije (sada 32 strane, 317 dok.)
    lists.sort()
    print(f"proglasenih lista: {len(lists)}")
    for dt, num, name in lists:
        # izbegni cp1252 gresku u Windows konzoli
        try:
            print(f"  [{num}] dt={dt} {name[:80]}")
        except UnicodeEncodeError:
            print(f"  [{num}] dt={dt} {name[:80].encode('ascii','replace').decode()}")

    c = psycopg2.connect(os.environ["DATABASE_URL"])
    c.autocommit = True
    cur = c.cursor()
    cur.execute("SELECT id FROM elections WHERE slug='parlamentarni-2026'")
    eid = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(MAX(ballot_number), 0) FROM parties WHERE election_id=%s", (eid,))
    next_bn = cur.fetchone()[0] + 1
    for i, (dt, num, name) in enumerate(lists, start=1):
        color, minor = PALETTE[(i - 1) % len(PALETTE)], False
        for kw, col, mn in COLOR_RULES:
            if kw in name:
                color, minor = col, mn
                break
        cur.execute("SELECT id FROM parties WHERE election_id=%s AND name=%s", (eid, name))
        ex = cur.fetchone()
        if ex:
            cur.execute("UPDATE parties SET color_hex=%s, is_minority=%s, short_name=%s WHERE id=%s",
                        (color, minor, short_name(name), ex[0]))
            try:
                print(f"  upd {name[:60]} {color} min={minor}")
            except UnicodeEncodeError:
                print(f"  upd {name[:60].encode('ascii','replace').decode()} {color} min={minor}")
        else:
            cur.execute("INSERT INTO parties (election_id, name, short_name, ballot_number, color_hex, is_minority)"
                        " VALUES (%s,%s,%s,%s,%s,%s)",
                        (eid, name, short_name(name), next_bn, color, minor))
            try:
                print(f"  + bn={next_bn} {name[:60]} {color} min={minor}")
            except UnicodeEncodeError:
                print(f"  + bn={next_bn} {name[:60].encode('ascii','replace').decode()} {color} min={minor}")
            next_bn += 1
    cur.execute("SELECT ballot_number, short_name, color_hex, is_minority FROM parties WHERE election_id=%s ORDER BY ballot_number", (eid,))
    print("--- stanje 2026 ---")
    for r in cur.fetchall():
        try:
            print(" ", r)
        except UnicodeEncodeError:
            print(" ", str(r).encode('ascii','replace').decode())


if __name__ == "__main__":
    main()
