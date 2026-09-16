# -*- coding: utf-8 -*-
"""Ujedinjena SVG mapa Srbije v2 — bez nagadjanja koordinata.
Za svaki region: geo bbox iz serbia-regioni.geojson + SVG bbox iz RIK putanja.
Preslikavanje = uniformna razmera + translacija (samo scale+translate, cuva oblik):
  - geo (lon,lat) -> km-prostor: X = lon*cos(44°), Y = lat
  - SVG (x,y) -> normalizovano na geo bbox regiona (uz pro...veru orijentacije sidrima)
  - sve u zajednicki prostor: (X - 13.4) * 1000, (46.6 - Y) * 1000
Izlaz: frontend/public/data/rik-srbija.json (prepisuje v1).
"""
import json
import math
import re

SRC = "frontend/public/data/rik-opstine.json"
GEO = "frontend/public/data/serbia-regioni.geojson"
DST = "frontend/public/data/rik-srbija.json"

RS_BY_NAME = {
    "Београдски регион": "rs11",
    "Регион Војводине": "rs12",
    "Регион Шумадије и Западне Србије": "rs21",
    "Регион Јужне и Источне Србије": "rs22",
    "Регион Косово и Метохија": "rs23",
}

# sidra samo za proveru orijentacije (znak), ne za fit
ANCHORS = [
    ("СТАРИ ГРАД", 20.45, 44.82), ("ЗЕМУН", 20.39, 44.85),
    ("СУБОТИЦА", 19.68, 46.10), ("НОВИ САД", 19.84, 45.25),
    ("ШАБАЦ", 19.69, 44.75), ("КРАГУЈЕВАЦ", 20.92, 44.01),
    ("СМЕДЕРЕВО", 20.93, 44.66), ("МЕДИЈАНА", 21.90, 43.32),
    ("ЛЕСКОВАЦ", 21.95, 43.00), ("ПРИШТИНА", 21.17, 42.66), ("ПЕЋ", 20.29, 42.66),
]

NUM = re.compile(r"-?\d+(?:\.\d+)?")
TOKEN = re.compile(r"[MmLlCcQqZzHhVv]|-?\d+(?:\.\d+)?")
COS44 = math.cos(math.radians(44.0))


def coords_of(path):
    c = [float(x) for x in NUM.findall(path)]
    return c[0::2], c[1::2]


def geo_bbox(feat):
    xs, ys = [], []

    def walk(g):
        if isinstance(g, (int, float)):
            return
        if isinstance(g, list):
            if len(g) == 2 and all(isinstance(v, (int, float)) for v in g):
                xs.append(g[0])
                ys.append(g[1])
            else:
                for x in g:
                    walk(x)

    walk(feat["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def transform_path(path, fn):
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
                X, Y = fn(nums[k], nums[k + 1])
                out.append(f"{X:.1f}")
                out.append(f"{Y:.1f}")
        elif c == "C":
            for k in range(0, len(nums), 6):
                for j in range(3):
                    X, Y = fn(nums[k + 2 * j], nums[k + 2 * j + 1])
                    out.append(f"{X:.1f}")
                    out.append(f"{Y:.1f}")
        elif c == "Q":
            for k in range(0, len(nums), 4):
                for j in range(2):
                    X, Y = fn(nums[k + 2 * j], nums[k + 2 * j + 1])
                    out.append(f"{X:.1f}")
                    out.append(f"{Y:.1f}")
        else:
            out.extend(str(v) for v in nums)
    return " ".join(out)


def main():
    rik = json.load(open(SRC, encoding="utf-8"))["regions"]
    geo = json.load(open(GEO, encoding="utf-8"))["features"]
    by_rk = {}
    for f in geo:
        rk = RS_BY_NAME[f["properties"]["name"]]
        by_rk[rk] = geo_bbox(f)
    anchor_shapes = {}
    for rk, rv in rik.items():
        for m in rv["municipalities"]:
            anchor_shapes[m["name"]] = (rk, m["path"])
    # provera orijentacije po regionima
    orient = {}
    for rk in rik:
        sx = [(coords_of(anchor_shapes[a][1]), lon) for a, lon, lat in ANCHORS
              if a in anchor_shapes and anchor_shapes[a][0] == rk]
        sy = [(coords_of(anchor_shapes[a][1]), lat) for a, lon, lat in ANCHORS
              if a in anchor_shapes and anchor_shapes[a][0] == rk]

        def meanx(item):
            (xs, ys), _ = item
            return sum(xs) / len(xs)

        def meany(item):
            (xs, ys), _ = item
            return sum(ys) / len(ys)
        # znak korelacije: da li veci svg-x prati veci lon?
        xs = sorted(sx, key=meanx)
        x_sign = 1 if xs[-1][1] >= xs[0][1] else -1
        ys = sorted(sy, key=meany)
        # ocekujemo: veci svg-y -> manji lat (y raste nadole)
        y_sign = -1 if ys[-1][1] <= ys[0][1] else 1
        orient[rk] = (x_sign, y_sign)
        print(f"{rk}: x_sign={x_sign:+d} y_sign={y_sign:+d} (ocekivano +1,-1) sidra={len(sx)}")
    out = []
    for rk, rv in rik.items():
        lon0, lat0, lon1, lat1 = by_rk[rk]
        # SVG bbox regiona
        sx0 = sy0 = float("inf")
        sx1 = sy1 = float("-inf")
        for m in rv["municipalities"]:
            xs, ys = coords_of(m["path"])
            sx0, sy0 = min(sx0, min(xs)), min(sy0, min(ys))
            sx1, sy1 = max(sx1, max(xs)), max(sy1, max(ys))
        # geo u km-prostoru
        gx0, gx1 = lon0 * COS44, lon1 * COS44
        gy0, gy1 = lat0, lat1
        # uniformna razmera (cuva oblik) + centriranje
        s = min((gx1 - gx0) / (sx1 - sx0), (gy1 - gy0) / (sy1 - sy0))
        ox = (gx0 + gx1) / 2 - s * (sx0 + sx1) / 2 * orient[rk][0]
        oy = (gy0 + gy1) / 2 - s * (sy0 + sy1) / 2 * orient[rk][1]

        def fn(x, y, s=s, ox=ox, oy=oy, o=orient[rk]):
            return ((o[0] * s * x + ox - 13.4) * 1000.0,
                    (46.6 - (o[1] * s * y + oy)) * 1000.0)

        for m in rv["municipalities"]:
            nd = transform_path(m["path"], fn)
            c = [float(v) for v in NUM.findall(nd)]
            xs2, ys2 = c[0::2], c[1::2]
            out.append({"id": m["id"], "name": m["name"], "region": rk,
                        "cx": round((min(xs2) + max(xs2)) / 2, 1),
                        "cy": round((min(ys2) + max(ys2)) / 2, 1), "d": nd})
    W = int((22.9 - 13.4 - 13.4 + 13.4) * 1000)  # placeholder, preracunaj dole
    xs_all = [m["cx"] for m in out]
    ys_all = [m["cy"] for m in out]
    print(f"opseg X: {min(xs_all):.0f}..{max(xs_all):.0f}, Y: {min(ys_all):.0f}..{max(ys_all):.0f}")
    W = int(max(xs_all) + 120)
    H = int(max(ys_all) + 120)
    json.dump({"width": W, "height": H, "municipalities": out},
              open(DST, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"snimljeno {DST}: {len(out)} opstina, {W}x{H}")


if __name__ == "__main__":
    main()
