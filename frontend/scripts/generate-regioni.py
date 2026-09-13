import json
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

# putanje
okruzi_path = Path(__file__).parent.parent / "public" / "data" / "serbia-okruzi.geojson"
out_path = Path(__file__).parent.parent / "public" / "data" / "serbia-regioni.geojson"

OKRUG_TO_RIK = {
  "Grad Beograd": "Београдски регион",
  "Severnobački okrug": "Регион Војводине",
  "Srednjebanatski okrug": "Регион Војводине",
  "Severnobanatski okrug": "Регион Војводине",
  "Južnobanatski okrug": "Регион Војводине",
  "Zapadnobački okrug": "Регион Војводине",
  "Južnobački okrug": "Регион Војводине",
  "Sremski okrug": "Регион Војводине",
  "Sremski": "Регион Војводине",
  "Zlatiborski okrug": "Регион Шумадије и Западне Србије",
  "Kolubarski okrug": "Регион Шумадије и Западне Србије",
  "Mačvanski okrug": "Регион Шумадије и Западне Србије",
  "Moravički okrug": "Регион Шумадије и Западне Србије",
  "Pomoravski okrug": "Регион Шумадије и Западне Србије",
  "Rasinski okrug": "Регион Шумадије и Западне Србије",
  "Raški okrug": "Регион Шумадије и Западне Србије",
  "Šumadijski okrug": "Регион Шумадије и Западне Србије",
  "Borski okrug": "Регион Јужне и Источне Србије",
  "Braničevski okrug": "Регион Јужне и Источне Србије",
  "Zaječarski okrug": "Регион Јужне и Источне Србије",
  "Zaječarski": "Регион Јужне и Источне Србије",
  "Jablanički okrug": "Регион Јужне и Источне Србије",
  "Nišavski okrug": "Регион Јужне и Источне Србије",
  "Pirotski okrug": "Регион Јужне и Источне Србије",
  "Podunavski okrug": "Регион Јужне и Источне Србије",
  "Pčinjski okrug": "Регион Јужне и Источне Србије",
  "Toplički okrug": "Регион Јужне и Источне Србије",
  "Kosovski okrug": "Регион Косово и Метохија",
  "Kosovski": "Регион Косово и Метохија",
  "Pećki okrug": "Регион Косово и Метохија",
  "Pećki": "Регион Косово и Метохија",
  "Prizrenski okrug": "Регион Косово и Метохија",
  "Prizrenski": "Регион Косово и Метохија",
  "Kosovsko-mitrovački okrug": "Регион Косово и Метохија",
  "Kosovsko-pomoravski okrug": "Регион Косово и Метохија",
  "Kosovsko-Pomoravski okrug": "Регион Косово и Метохија",
  "Kosovsko-mitrovacki okrug": "Регион Косово и Метохија",
  "Kosovskomitrovički okrug": "Регион Косово и Метохија",
}

data = json.loads(okruzi_path.read_text(encoding="utf-8"))
features = data["features"]

# grupiši
groups: dict[str, list] = {}
for f in features:
    name = (f["properties"].get("name") or "").strip()
    rik = OKRUG_TO_RIK.get(name)
    if not rik:
        print(f"WARN no mapping for {name!r}")
        continue
    groups.setdefault(rik, []).append(shape(f["geometry"]))

print("Groups:", {k: len(v) for k,v in groups.items()})

out_features = []
for rik_name, geoms in groups.items():
    merged = unary_union(geoms)
    # ensure valid
    if not merged.is_valid:
        merged = merged.buffer(0)
    out_features.append({
        "type": "Feature",
        "properties": {"name": rik_name},
        "geometry": mapping(merged)
    })

out = {"type": "FeatureCollection", "features": out_features}
out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out_path} with {len(out_features)} features")
for f in out_features:
    geom_type = f["geometry"]["type"]
    print(f["properties"]["name"], geom_type, "area", shape(f["geometry"]).area)
