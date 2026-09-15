# -*- coding: utf-8 -*-
"""
Istorijski parlamentarni izbori 2012-2022 u postojecu semu.

Izvori (smestiti u collector/raw/):
  2012-bm.xls: https://arhiva.rik.parlament.gov.rs/doc/arhiva/poslanici/2012/4.%202012%20np%20rzs.xls
  2014-bm.xls: https://arhiva.rik.parlament.gov.rs/doc/arhiva/poslanici/2014/4.%20Rezultati%20izbora%20po%20BM2014%20np%20rzs.xls
  2016-bm.xls: https://arhiva.rik.parlament.gov.rs/doc/izbori-2016/rezultati/3.%20Rezultati%20izbora%20po%20birackim%20mestima.XLS
  2020-bm.xls: https://www.rik.parlament.gov.rs/extfile/sr/9428/3%20po%20bir%20mesrima1.XLS
  2022: python sddb_fetch.py --sub 07021001 --out raw/2022-glasovi.json (+ mandati 07020602..07021002)
Formati:
  2012/2014 - hijerarhijski (parovi Broj/%, agregatni redovi + adresar)
  2016/2020 - flat (12 meta kolona + liste)
  2022      - SDDB JSON (nivo opstine, bez birackih mesta)

Upotreba:
  python import_historical.py --year 2020            # dry-run: strukture, mapiranja, provere
  python import_historical.py --year 2020 --commit   # upis u bazu
  python import_historical.py --year all --commit
  python import_historical.py --year 2020 --commit --redo   # obrisi postojeci unos pa ponovo
"""
import argparse
import json
import logging
import os
import re
import sys
from difflib import SequenceMatcher

import xlrd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/izbori")
PG_URL = DATABASE_URL  # cista URL za psycopg COPY (bez SQLAlchemy dijalekta)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("import_hist")

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

PALETTE = ["#e63946", "#457b9d", "#7c3aed", "#78716c", "#f59e0b", "#0ea5e9",
           "#22c55e", "#a855f7", "#14b8a6", "#94a3b8", "#3b82d6", "#f97316",
           "#84cc16", "#eab308", "#64748b", "#ef4444", "#8b5cf6", "#06b6d4",
           "#ec4899", "#14b8a6", "#f43f5e", "#8b5cf6"]

CONFIG = {
    2012: {"slug": "parlamentarni-2012", "name": "Parlamentarni izbori 2012",
           "date": "2012-05-06", "threshold": 5, "src": "xls",
           "file": "2012-bm.xls", "sheet": "Парламентарни", "hrow": 1, "layout": "hier",
           "addr_sheet": "Бирачка места",
           "mandati": "2012-mandati.json",
           "minor": ["MADARA", "SDA", "ZAJEDNO", "ALBANACA", "NACIONALNIH ZAJEDNICA"]},
    2014: {"slug": "parlamentarni-2014", "name": "Parlamentarni izbori 2014",
           "date": "2014-03-16", "threshold": 5, "src": "xls",
           "file": "2014-bm.xls", "sheet": "Резултати ", "hrow": 1, "layout": "hier",
           "addr_sheet": "Адресар бирачких места",
           "mandati": "2014-mandati.json",
           "minor": ["MADARA", "SDA", "DEMOKRATSKO DELOVANJE"]},
    2016: {"slug": "parlamentarni-2016", "name": "Parlamentarni izbori 2016",
           "date": "2016-04-24", "threshold": 5, "src": "xls",
           "file": "2016-bm.xls", "sheet": 0, "hrow": 3, "layout": "flat",
           "mandati": "2016-mandati.json",
           "minor": ["MADARA", "ZUKORLI", "SDA", "DEMOKRATSKO DELOVANJE", "ZELENA STRANKA"]},
    2020: {"slug": "parlamentarni-2020", "name": "Parlamentarni izbori 2020",
           "date": "2020-06-21", "threshold": 3, "src": "xls",
           "file": "2020-bm.xls", "sheet": 0, "hrow": 0, "layout": "flat",
           "mandati": "2020-mandati.json",
           "minor": ["MADARA", "ZUKORLI", "PRAVDE I POMIRENJA", "SDA", "ALBANSKA DEMOKRATSKA"]},
    2022: {"slug": "parlamentarni-2022", "name": "Parlamentarni izbori 2022",
           "date": "2022-04-03", "threshold": 3, "src": "sddb",
           "file": "2022-glasovi.json",
           "mandati": "2022-mandati.json",
           "minor": ["MADARA", "MUFTIJIN", "SDA", "VOJVODINU", "ALBANACA", "ALTERNATIVA",
                     "RUSKI MANJINSKI", "ROMSKA PARTIJA"]},
}

_CYR = "АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШабвгдђежзијклљмнњопрстћуфхцчџш"
_LAT = ["A", "B", "V", "G", "D", "Đ", "E", "Ž", "Z", "I", "J", "K", "L", "Lj",
        "M", "N", "Nj", "O", "P", "R", "S", "T", "Ć", "U", "F", "H", "C", "Č", "Dž", "Š",
        "a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "lj",
        "m", "n", "nj", "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č", "dž", "š"]
_C2L = dict(zip(_CYR, _LAT))
_ASCII = str.maketrans("ČĆŽŠĐčćžšđ", "CCZSDcczsd")


def to_lat(s: str) -> str:
    return "".join(_C2L.get(ch, ch) for ch in (s or ""))


STRIP_PREFIX = ["GRADSKAOPSTINA", "GRADSKEOPSTINE", "GRADSKIHOPSTINA",
                  "GRADSKA", "GRADSKE", "OPSTINA", "GRAD"]
# rucne prečice: kljuc iz fajla -> kljuc u bazi
ALIASES = {
    "PETROVAC": "PETROVACNAMLAVI",  # 2014/2012: uz Malo Crniće (Branicevski okrug)
}


def norm_key(s: str) -> str:
    t = to_lat(s or "").upper().translate(_ASCII)
    t = re.sub(r"[^A-Z0-9]", "", t)
    for p in STRIP_PREFIX:
        if t.startswith(p) and len(t) > len(p) + 2:
            t = t[len(p):]
            break
    t = re.sub(r"GRAD$", "", t)  # 'Vranje-grad'
    return t


def lookup_municipality(key: str, by_name: dict):
    if key in ALIASES:
        key = ALIASES[key]
        if key is None:
            return []
    cands = by_name.get(key, [])
    if not cands and key.startswith("NIS") and len(key) > 5:
        cands = by_name.get(key[3:], [])  # 'Nis - Medijana' -> 'Medijana'
    return cands


def num(v) -> int | None:
    if v is None or (isinstance(v, str) and not v.strip()) or v == "-":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(float(str(v).replace(".", "").replace(",", ".").replace("\xa0", "").strip()))
    except ValueError:
        return None


def parse_flat(path: str, sheet, hrow: int):
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(sheet) if isinstance(sheet, int) else wb.sheet_by_name(sheet)
    header = [str(sh.cell_value(hrow, c)).strip() for c in range(sh.ncols)]
    lists = [{"bn": i - 11, "name": header[i]} for i in range(12, sh.ncols) if header[i]]
    stations = []
    for r in range(hrow + 1, sh.nrows):
        st = str(sh.cell_value(r, 4)).strip()
        if not st:
            continue
        code = re.sub(r"\.0$", "", str(sh.cell_value(r, 2)).strip())
        votes = [num(sh.cell_value(r, 12 + i)) or 0 for i in range(len(lists))]
        stations.append({
            "code": code if re.fullmatch(r"\d+", code) else None,
            "mun_name": str(sh.cell_value(r, 3)).strip(),
            "okrug": str(sh.cell_value(r, 1)).strip(),
            "st": st.rstrip("0").rstrip(".") if "." in st else st,
            "registered": num(sh.cell_value(r, 5)),
            "voted": num(sh.cell_value(r, 8)),
            "invalid": num(sh.cell_value(r, 10)),
            "valid": num(sh.cell_value(r, 11)),
            "votes": votes,
        })
    return lists, stations


def parse_hier(path: str, sheet, hrow: int):
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(sheet) if isinstance(sheet, int) else wb.sheet_by_name(sheet)
    header = [str(sh.cell_value(hrow, c)).strip() for c in range(sh.ncols)]
    lists, colmap = [], {}
    bn = 0
    for c in range(12, sh.ncols, 2):
        if header[c]:
            bn += 1
            lists.append({"bn": bn, "name": header[c]})
            colmap[bn] = c
    stations, aggregates = [], 0
    for r in range(hrow + 2, sh.nrows):
        terr = str(sh.cell_value(r, 0)).strip()
        st = str(sh.cell_value(r, 1)).strip()
        if not terr:
            continue
        if not st or st in ("0", "0.0"):
            aggregates += 1
            continue
        votes = [num(sh.cell_value(r, colmap[i + 1])) or 0 for i in range(len(lists))]
        stations.append({
            "code": None, "mun_name": terr, "okrug": None,
            "st": st.rstrip("0").rstrip(".") if "." in st else st,
            "registered": num(sh.cell_value(r, 2)),
            "voted": num(sh.cell_value(r, 3)),
            "invalid": num(sh.cell_value(r, 8)),
            "valid": num(sh.cell_value(r, 10)),
            "votes": votes,
        })
    log.info("  hijerarhijski: %d stanica, %d agregatnih redova preskoceno", len(stations), aggregates)
    return lists, stations


def parse_addr(path: str, sheet: str):
    try:
        wb = xlrd.open_workbook(path)
        sh = wb.sheet_by_name(sheet)
    except Exception as e:
        log.warning("  nema adresara %s: %s", sheet, e)
        return {}
    out = {}
    for r in range(sh.nrows):
        terr = str(sh.cell_value(r, 0)).strip()
        st = str(sh.cell_value(r, 1)).strip()
        name = str(sh.cell_value(r, 2)).strip()
        addr = str(sh.cell_value(r, 3)).strip() if sh.ncols > 3 else ""
        if terr and st and name and "Територија" not in terr and "Адресар" not in terr:
            out[(norm_key(terr), st.rstrip("0").rstrip(".") if "." in st else st)] = (name, addr)
    log.info("  adresar: %d unosa", len(out))
    return out


def parse_sddb(path: str):
    d = json.load(open(path, encoding="utf-8"))
    rows = [r for r in d["rows"] if r.get("Vrsta podatka") == "1"]
    # zvanican redosled sa glasackog listica: NP202201 -> 1 ...
    codes = json.load(open(os.path.join(RAW, "2022-list-codes.json"), encoding="utf-8"))
    ordered = sorted(codes.items(), key=lambda kv: kv[0])
    names = [v for _, v in ordered]
    have = {r["Izborna lista"] for r in rows}
    missing = [n for n in names if n not in have]
    if missing:
        log.warning("  liste bez glasova u SDDB: %s", missing)
    lists = [{"bn": i + 1, "name": n} for i, n in enumerate(names) if n in have]
    mun_votes: dict[str, dict] = {}
    for r in rows:
        t = r["Teritorija - NSTJ"]
        v = num(r.get("Vrednost")) or 0
        mun_votes.setdefault(t, {})[r["Izborna lista"]] = v
    return lists, mun_votes


AGG_WORDS = ["OKRUG", "REPUBLIKASRBIJA", "CENTRALNASRBIJA", "VOJVODINA",
             "KOSOVOIMETOHIJA", "GRADBEOGRAD", "INOSTRANSTVO",
             "ZAVODIZAZIVRSENJE", "ZAVODI"]


def load_municipalities(conn):
    rows = conn.execute(text("SELECT id, name, rzs_code, region FROM municipalities")).fetchall()
    by_code, by_name = {}, {}
    for r in rows:
        if r.rzs_code:
            by_code[str(r.rzs_code).strip()] = {"id": r.id, "name": r.name, "region": r.region}
        by_name.setdefault(norm_key(r.name), []).append(
            {"id": r.id, "name": r.name, "code": r.rzs_code, "region": r.region})
    return by_code, by_name


def load_region2023(conn):
    rows = conn.execute(text(
        "SELECT municipality_id, rik_region_id FROM election_municipality_codes WHERE election_id = 2")).fetchall()
    return {r.municipality_id: r.rik_region_id for r in rows}


def resolve_municipality(st, by_code, by_name, inostranstvo_id, zavodi_id, report):
    if st.get("code") and st["code"] in by_code:
        return by_code[st["code"]]["id"], False
    key = norm_key(st["mun_name"])
    cands = lookup_municipality(key, by_name)
    if len(cands) == 1:
        return cands[0]["id"], False
    if len(cands) > 1:
        report["viseznacne"].setdefault(st["mun_name"], [c["name"] for c in cands])
        return cands[0]["id"], False
    if "ZAVOD" in key and zavodi_id:
        return zavodi_id, False
    if any(w in key for w in AGG_WORDS):
        report["agregati"].add(st["mun_name"])
        return None, True
    report["nema_opstine"].setdefault(st["mun_name"], 0)
    report["nema_opstine"][st["mun_name"]] += 1
    return inostranstvo_id, False


def map_seats(lists, mandati_path, minor_words):
    md = json.load(open(os.path.join(RAW, mandati_path), encoding="utf-8"))
    mrows = md["rows"]
    mapping = []
    for i, li in enumerate(lists):
        best, best_r, best_j = None, -1.0, -1
        for j, m in enumerate(mrows):
            r = SequenceMatcher(None, norm_key(li["name"]), norm_key(m["Izborna lista"])).ratio()
            # bonus za isti redosled na listicu
            r += 0.05 if abs(j - i) <= 1 else 0.0
            if r > best_r:
                best, best_r, best_j = m, r, j
        ok = best_r >= 0.55 or (best_j == i and best_r >= 0.20)
        mapping.append({"bn": li["name"][:60], "mandati": best["Izborna lista"][:60] if best else None,
                        "seats": int(float(str(best["Vrednost"]).replace(",", "."))) if best else 0,
                        "ratio": round(best_r, 2), "ok": ok})
    total = sum(m["seats"] for m in mapping)
    return mapping, total, mrows


def clean_name(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def short_name(name: str, bn: int) -> str:
    s = re.sub(r"^\s*\d+\.\s*", "", name).strip()[:50]
    return s or f"Lista {bn}"


def delete_election(conn, eid: int):
    for tbl, col in [("results", "election_id"), ("municipality_results", "election_id"),
                     ("municipality_stats", "election_id"),
                     ("election_station_codes", "election_id"),
                     ("election_municipality_codes", "election_id"),
                     ("parties", "election_id")]:
        conn.execute(text(f"DELETE FROM {tbl} WHERE {col} = :eid"), {"eid": eid})
    conn.execute(text("DELETE FROM elections WHERE id = :eid"), {"eid": eid})
    log.warning("  obrisani postojeci podaci za election_id=%s", eid)


def ingest_year(conn, year: int, commit: bool, redo: bool):
    cfg = CONFIG[year]
    log.info("=" * 70)
    log.info("%s (%s) -- %s", cfg["name"], cfg["date"], "UPIS" if commit else "DRY-RUN")
    if cfg["src"] == "xls":
        path = os.path.join(RAW, cfg["file"])
        if cfg["layout"] == "flat":
            lists, stations = parse_flat(path, cfg["sheet"], cfg["hrow"])
        else:
            lists, stations = parse_hier(path, cfg["sheet"], cfg["hrow"])
        addr = parse_addr(path, cfg["addr_sheet"]) if cfg.get("addr_sheet") else {}
        mun_votes = None
    else:
        lists, mun_votes = parse_sddb(os.path.join(RAW, cfg["file"]))
        stations, addr = [], {}
    for li in lists:
        li["name"] = clean_name(li["name"])
    log.info("  lista: %d, stanica: %d, opstina(SDDB): %d",
             len(lists), len(stations), len(mun_votes) if mun_votes else 0)

    mapping, seat_total, mrows = map_seats(lists, cfg["mandati"], cfg["minor"])
    print(f"--- {year} mapiranje mandata (zbir={seat_total}, ocekivano 250) ---")
    for m in mapping:
        flag = "" if m["ok"] else "  <-- PROVERI RUCNO!"
        print(f"  {m['ratio']:.2f} s={m['seats']:3d}  {m['bn'][:55]:55s} <- {m['mandati'][:55]}{flag}")
    low = [m for m in mapping if not m["ok"]]

    by_code, by_name = load_municipalities(conn)
    region2023 = load_region2023(conn)
    ino = by_name.get(norm_key("Иностранство"), [{}])[0].get("id")
    zav = by_code.get("55001", {}).get("id")
    report = {"nema_opstine": {}, "viseznacne": {}, "agregati": set()}

    if stations:
        mun_ids = {}
        for st in stations:
            mid, skip = resolve_municipality(st, by_code, by_name, ino, zav, report)
            if skip or mid is None:
                continue
            mun_ids.setdefault(mid, []).append(st)
        print(f"--- {year} opstine: {len(mun_ids)} sa stanicama ---")
        if report["nema_opstine"]:
            print("  NEPOZNATE TERITORIJE (idu u inostranstvo):")
            for k, v in sorted(report["nema_opstine"].items(), key=lambda x: -x[1])[:20]:
                print(f"    {v:5d}x  {k}")
        if report["viseznacne"]:
            print("  VISEZNACNE:", dict(list(report["viseznacne"].items())[:10]))
        # nacionalna kontrola
        tot_votes = sum(sum(st["votes"]) for sts in mun_ids.values() for st in sts)
        tot_voted = sum((st["voted"] or 0) for sts in mun_ids.values() for st in sts)
        top = sorted(range(len(lists)), key=lambda i: -sum(st["votes"][i] for sts in mun_ids.values() for st in sts))[:6]
        print(f"  stanica sa podacima: {sum(len(v) for v in mun_ids.values())}, valid~{tot_votes}, glasalo~{tot_voted}")
        for i in top:
            v = sum(st["votes"][i] for sts in mun_ids.values() for st in sts)
            print(f"    {v:8d} {100*v/(tot_votes or 1):5.2f}%  {lists[i]['name'][:70]}")
    else:
        leaf_path = os.path.join(RAW, "2022-municipalities.json")
        leaves = set(json.load(open(leaf_path, encoding="utf-8"))) if os.path.exists(leaf_path) else None
        mun_ids = {}
        for code in mun_votes:
            if leaves is not None and code not in leaves:
                report["agregati"].add(f"code:{code}")
                continue
            if code in by_code:
                mun_ids[by_code[code]["id"]] = code
            else:
                report["nema_opstine"].setdefault(f"code:{code}", 0)
                report["nema_opstine"][f"code:{code}"] += 1
        if report["agregati"]:
            print("  agregati preskoceni:", sorted(report["agregati"]))
        print(f"--- {year} SDDB opstine: {len(mun_ids)} mapirano kodom, nepoznato: {len(report['nema_opstine'])} ---")
        if report["nema_opstine"]:
            print("  NEPOZNATI KODOVI:", dict(list(report["nema_opstine"].items())[:20]))
        tot = sum(sum(v.values()) for v in mun_votes.values())
        print(f"  ukupno valid: {tot}")

    if low and commit:
        log.error("  ima nesigurnih mapiranja mandata - prekini bez --force")
        return False
    if not commit:
        log.info("  DRY-RUN kraj (nista nije upisano)")
        return True

    # ---- UPIS (brzi put: COPY bulk, 1 commit) ----
    import psycopg
    ex = conn.execute(text("SELECT id FROM elections WHERE slug = :s"), {"s": cfg["slug"]}).fetchone()
    if ex:
        if not redo:
            log.error("  izbori %s vec postoje (id=%s); dodaj --redo za ponovni unos", cfg["slug"], ex.id)
            return False
        delete_election(conn, ex.id)
        conn.commit()
    pg = psycopg.connect(PG_URL)
    cur = pg.cursor()
    cur.execute(
        "INSERT INTO elections (slug, name, election_type, election_date, status, rik_type)"
        " VALUES (%s, %s, 'parliamentary', %s, 'closed', 2) RETURNING id",
        (cfg["slug"], cfg["name"], cfg["date"]))
    eid = cur.fetchone()[0]

    party_ids = {}
    for i, li in enumerate(lists):
        m = mapping[i]
        is_min = any(w in norm_key(li["name"]) for w in cfg["minor"])
        cur.execute(
            "INSERT INTO parties (election_id, name, short_name, ballot_number, color_hex,"
            " is_minority, official_seats) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (eid, li["name"].strip(), short_name(li["name"], li["bn"]), li["bn"],
             PALETTE[(li["bn"] - 1) % len(PALETTE)], is_min, m["seats"]))
        party_ids[li["bn"]] = cur.fetchone()[0]
    log.info("  upisano %d stranaka", len(party_ids))

    # emc za sve opstine izbora
    emc_rows = []
    for mid in mun_ids:
        rid = region2023.get(mid)
        if rid is None:
            log.warning("  opstina id=%s nema region 2023 mape!", mid)
            continue
        emc_rows.append((eid, mid, rid, mid))
    cur.executemany(
        "INSERT INTO election_municipality_codes (election_id, municipality_id,"
        " rik_region_id, rik_mun_value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        emc_rows)

    def copy_rows(table, cols, rows):
        import io
        buf = io.StringIO()
        for r in rows:
            buf.write("\t".join(
                "\\N" if v is None else ("true" if v is True else ("false" if v is False
                else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", " ")))
                for v in r) + "\n")
        buf.seek(0)
        with cur.copy(f"COPY {table} ({','.join(cols)}) FROM STDIN") as cp:
            while True:
                chunk = buf.read(1 << 20)
                if not chunk:
                    break
                cp.write(chunk)

    if stations:
        pre = conn.execute(text("SELECT municipality_id, name FROM polling_stations")).fetchall()
        seen_names = {(r.municipality_id, r.name) for r in pre}
        jobs, all_mun_stats, all_mun_res = [], [], []
        for mid, sts in mun_ids.items():
            agg_votes = [0] * len(lists)
            reg = vot = val = inv = 0
            for st in sts:
                key = (norm_key(st["mun_name"]), st["st"])
                aname, aaddr = addr.get(key, (None, None))
                base = clean_name(aname or f"BM {st['st']}")
                sname = base
                k = 1
                while (mid, sname) in seen_names:
                    k += 1
                    sname = f"{base} ({k})"
                seen_names.add((mid, sname))
                jobs.append((mid, sname, clean_name(aaddr) if aaddr else None, st))
                for i in range(len(lists)):
                    agg_votes[i] += st["votes"][i]
                reg += st["registered"] or 0
                vot += st["voted"] or 0
                val += st["valid"] or 0
                inv += st["invalid"] or 0
            all_mun_stats.append((eid, mid, vot, reg, val, inv, len(sts), len(sts)))
            for i in range(len(lists)):
                if agg_votes[i]:
                    all_mun_res.append((eid, mid, party_ids[i + 1], agg_votes[i]))
        # id-evi unapred iz sekvence (1 round-trip), pa COPY bez RETURNING
        cur.execute("SELECT nextval('polling_stations_id_seq') FROM generate_series(1, %s)", (len(jobs),))
        new_ids = [r[0] for r in cur.fetchall()]
        log.info("  COPY %d stanica + rezultati...", len(jobs))
        copy_rows("polling_stations",
                  ["id", "municipality_id", "name", "address", "registered_voters"],
                  [(sid, mid, n, a, j["registered"]) for sid, (mid, n, a, j) in zip(new_ids, jobs)])
        res_rows = []
        for sid, (mid, n, a, st) in zip(new_ids, jobs):
            for i in range(len(lists)):
                res_rows.append((eid, sid, party_ids[i + 1], st["votes"][i], True,
                                 st["valid"], st["invalid"], st["voted"]))
        copy_rows("results",
                  ["election_id", "polling_station_id", "party_id", "votes",
                   "is_processed", "valid_ballots", "invalid_ballots", "total_voted"],
                  res_rows)
        copy_rows("municipality_stats",
                  ["election_id", "municipality_id", "total_voted", "registered_voters",
                   "valid_ballots", "invalid_ballots", "processed_stations", "total_stations"],
                  all_mun_stats)
        copy_rows("municipality_results",
                  ["election_id", "municipality_id", "party_id", "votes"], all_mun_res)
        pg.commit()
        log.info("  upisano stanica: %d, mun_stats: %d, mun_results: %d",
                 len(jobs), len(all_mun_stats), len(all_mun_res))
    else:
        stats, res = [], []
        for mid, code in mun_ids.items():
            lv = mun_votes[code]
            for i, li in enumerate(lists):
                v = lv.get(li["name"], 0)
                if v:
                    res.append((eid, mid, party_ids[li["bn"]], v))
            stats.append((eid, mid, 0, 0))
        copy_rows("municipality_stats",
                  ["election_id", "municipality_id", "processed_stations", "total_stations"], stats)
        copy_rows("municipality_results",
                  ["election_id", "municipality_id", "party_id", "votes"], res)
        pg.commit()
        log.info("  upisano mun_stats: %d, mun_results: %d", len(stats), len(res))
    pg.close()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, help="2012/2014/2016/2020/2022/all")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--redo", action="store_true")
    args = ap.parse_args()
    years = sorted(CONFIG) if args.year == "all" else [int(args.year)]
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    ok = True
    with engine.connect() as conn:
        for y in years:
            if not ingest_year(conn, y, args.commit, args.redo):
                ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

