# -*- coding: utf-8 -*-
"""Ujedinjena SVG mapa Srbije iz 5 RIK regiona.
Svaki region ima svoj viewBox/koordinatni sistem. Metod: za svaki region
resavamo afin transform SVG->(lon,lat) najmanjim kvadratima preko sidrenih
gradova, pa sve putanje preslikamo u zajednicki prostor:
  X = (lon - 18.6) * 1000, Y = (46.5 - lat) * 1000
Izlaz: frontend/public/data/rik-srbija.json {width,height,municipalities:[{id,name,region,cx,cy,d}]}
"""
import json
import re
import numpy as np

SRC = "frontend/public/data/rik-opstine.json"
DST = "frontend/public/data/rik-srbija.json"

# (RIK ime, lon, lat)
ANCHORS = [
    ("СТАРИ ГРАД", 20.45, 44.82), ("ЗЕМУН", 20.39, 44.85), ("ОБРЕНОВАЦ", 20.20, 44.66),
    ("МЛАДЕНОВАЦ", 20.69, 44.44), ("ЛАЗАРЕВАЦ", 20.26, 44.38),
    ("СУБОТИЦА", 19.68, 46.10), ("СОМБОР", 19.11, 45.77), ("НОВИ САД", 19.84, 45.25),
    ("ЗРЕЊАНИН", 20.38, 45.38), ("ПАНЧЕВО", 20.64, 44.87),
    ("СРЕМСКА МИТРОВИЦА", 19.61, 44.97), ("ВРШАЦ", 21.30, 45.12),
    ("ШАБАЦ", 19.69, 44.75), ("ВАЉЕВО", 19.88, 44.27), ("УЖИЦЕ", 19.85, 43.86),
    ("ЧАЧАК", 20.35, 43.89), ("КРАЉЕВО", 20.68, 43.72), ("КРАГУЈЕВАЦ", 20.92, 44.01),
    ("СМЕДЕРЕВО", 20.93, 44.66), ("ПОЖАРЕВАЦ", 21.19, 44.62), ("МЕДИЈАНА", 21.90, 43.32),
    ("ЛЕСКОВАЦ", 21.95, 43.00), ("ВРАЊЕ", 21.90, 42.55), ("ПИРОТ", 22.58, 43.15),
    ("ЗАЈЕЧАР", 22.28, 43.90), ("НЕГОТИН", 22.53, 44.23),
    ("ПРИШТИНА", 21.17, 42.66), ("ПЕЋ", 20.29, 42.66), ("ГЊИЛАНЕ", 21.47, 42.46),
    ("КОСОВСКА МИТРОВИЦА", 20.87, 42.89), ("ПРИЗРЕН", 20.74, 42.21),
    ("УРОШЕВАЦ", 21.15, 42.37),
]

NUM = re.compile(r"-?\d+(?:\.\d+)?")


def coords_of(path: str):
    return [float(x) for x in NUM.findall(path)]


def centroid(path: str):
    c = coords_of(path)
    xs = c[0::2]
    ys = c[1::2]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def fit_affine(pts):
    """pts: [(x, y, lon, lat)] -> ((a,b,c),(d,e,f)) lon=a*x+b*y+c, lat=d*x+e*y+f."""
    A, blon, blat = [], [], []
    for x, y, lon, lat in pts:
        A.append([x, y, 1])
        blon.append(lon)
        blat.append(lat)
    A = np.array(A)
    lon_p, *_ = np.linalg.lstsq(A, np.array(blon), rcond=None)
    lat_p, *_ = np.linalg.lstsq(A, np.array(blat), rcond=None)
    # reziduali u stepenima
    rl = A @ lon_p - blon
    rt = A @ lat_p - blat
    err = float(np.sqrt((rl ** 2 + rt ** 2).mean()))
    return lon_p, lat_p, err


TOKEN = re.compile(r"[MmLlCcQqZzHhVv]|-?\d+(?:\.\d+)?")


def transform_path(path: str, lon_p, lat_p, lon0=18.6, lat1=46.5, s=1000.0):
    def conv(x, y):
        lon = lon_p[0] * x + lon_p[1] * y + lon_p[2]
        lat = lat_p[0] * x + lat_p[1] * y + lat_p[2]
        return ((lon - lon0) * s, (lat1 - lat) * s)

    toks = TOKEN.findall(path)
    out = []
    i = 0
    cmd = ""
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            out.append(t)
            i += 1
            continue
        nums = []
        while i < len(toks) and not toks[i].isalpha():
            nums.append(float(toks[i]))
            i += 1
        c = cmd.upper()
        if c in ("M", "L"):
            for k in range(0, len(nums), 2):
                X, Y = conv(nums[k], nums[k + 1])
                out.append(f"{X:.1f}")
                out.append(f"{Y:.1f}")
        elif c == "C":
            for k in range(0, len(nums), 6):
                for j in range(3):
                    X, Y = conv(nums[k + 2 * j], nums[k + 2 * j + 1])
                    out.append(f"{X:.1f}")
                    out.append(f"{Y:.1f}")
        elif c == "Q":
            for k in range(0, len(nums), 4):
                for j in range(2):
                    X, Y = conv(nums[k + 2 * j], nums[k + 2 * j + 1])
                    out.append(f"{X:.1f}")
                    out.append(f"{Y:.1f}")
        elif c in ("H", "V"):
            out.extend(str(v) for v in nums)  # ne bi trebalo da postoji
        elif c == "Z":
            pass
        cmd = c if c in ("M", "L") else cmd
    return " ".join(out)


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    regions = d["regions"]
    by_name = {}
    for rk, rv in regions.items():
        for m in rv["municipalities"]:
            by_name.setdefault(m["name"], []).append((rk, m))
    missing = [a[0] for a in ANCHORS if a[0] not in by_name]
    print("ankeri kojih nema:", missing)
    used = {rk: [] for rk in regions}
    for name, lon, lat in ANCHORS:
        for rk, m in by_name.get(name, []):
            cx, cy = centroid(m["path"])
            used[rk].append((cx, cy, lon, lat))
    for rk, pts in used.items():
        print(f"{rk}: {len(pts)} ankera")
    fits = {}
    for rk, pts in used.items():
        lon_p, lat_p, err = fit_affine(pts)
        fits[rk] = (lon_p, lat_p)
        print(f"{rk}: greska fita {err:.4f} stepeni (~{err*111:.1f} km)")
    out = []
    for rk, rv in regions.items():
        lon_p, lat_p = fits[rk]
        for m in rv["municipalities"]:
            nd = transform_path(m["path"], lon_p, lat_p)
            c = coords_of(nd)
            xs, ys = c[0::2], c[1::2]
            out.append({"id": m["id"], "name": m["name"], "region": rk,
                        "cx": round((min(xs) + max(xs)) / 2, 1),
                        "cy": round((min(ys) + max(ys)) / 2, 1), "d": nd})
    W = int(46.5 and (22.9 - 18.6) * 1000)
    H = int((46.5 - 41.8) * 1000)
    json.dump({"width": W, "height": H, "municipalities": out},
              open(DST, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"snimljeno {DST}: {len(out)} opstina, {W}x{H}")


if __name__ == "__main__":
    main()
