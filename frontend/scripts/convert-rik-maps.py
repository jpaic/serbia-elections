"""Konvertuje RIK jVectorMap fajlove u JSON za frontend.
RIK kljucevi (data-id) = nas municipalities.rzs_code nakon bootstrap-a.
"""
import re, json
from pathlib import Path

SRC = Path(__file__).parent.parent / 'public' / 'data' / 'rik-maps'
OUT = Path(__file__).parent.parent / 'public' / 'data' / 'rik-opstine.json'

REGION_NAMES = {
    'rs11': 'Београдски регион',
    'rs12': 'Регион Војводине',
    'rs21': 'Регион Шумадије и Западне Србије',
    'rs22': 'Регион Јужне и Источне Србије',
    'rs23': 'Регион Косово и Метохија',
}

FILES = {
    'rs11': 'jquery-jvectormap-data-rs11-lcc-cr.js',
    'rs12': 'jquery-jvectormap-data-rs12-lcc-cr.js',
    'rs21': 'jquery-jvectormap-data-rs21-lcc-cr.js',
    'rs22': 'jquery-jvectormap-data-rs22-lcc-cr.js',
    'rs23': 'jquery-jvectormap-data-rs23-lcc-cr.js',
}

out = {"regions": {}}
total = 0
for code, fname in FILES.items():
    txt = (SRC / fname).read_text(encoding='utf-8')
    m = re.search(r'"width":\s*"?(\d+)"?,\s*"height":\s*"?(\d+)"?', txt)
    width, height = (int(m.group(1)), int(m.group(2))) if m else (750, 700)
    # Parsiraj paths: "ID": {"name": "...", "path": "..."}
    # Kljucevi su numeric (data-id, npr. "70203") ili alfanumericki (npr. "id20" za Decane na KiM)
    entries = re.findall(r'"([A-Za-z0-9]+)"\s*:\s*\{\s*"name":\s*"([^"]+)",\s*"path":\s*"([^"]+)"', txt)
    munis = [{"id": k, "name": name, "path": path} for k, name, path in entries]
    print(f"{code}: {len(munis)} opstina, {width}x{height}")
    for mu in munis[:3]:
        print(f"   {mu['id']} = {mu['name']}")
    out["regions"][code] = {
        "rik_region": REGION_NAMES[code],
        "width": width,
        "height": height,
        "municipalities": munis,
    }
    total += len(munis)

OUT.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
print(f"\nUkupno {total} opstina -> {OUT} ({OUT.stat().st_size//1024} KB)")

# Takodje napravi mapu data-id -> region za brzo filtriranje
mapping = {}
for code, region in out["regions"].items():
    for mu in region["municipalities"]:
        mapping[mu["id"]] = region["rik_region"]
map_path = OUT.parent / "rik-id-to-region.json"
map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"Mapping {len(mapping)} -> {map_path}")
