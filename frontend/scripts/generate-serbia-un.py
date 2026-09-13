import json
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

world_path = Path(__file__).parent.parent / "public" / "data" / "world.geojson"
out_path = Path(__file__).parent.parent / "public" / "data" / "serbia-world-un.geojson"

world = json.loads(world_path.read_text(encoding="utf-8"))

serbia_geom = None
kosovo_geom = None
for f in world["features"]:
    name = f["properties"].get("name") or f["properties"].get("NAME")
    if name == "Republic of Serbia":
        serbia_geom = shape(f["geometry"])
    elif name == "Kosovo":
        kosovo_geom = shape(f["geometry"])

if serbia_geom is None:
    raise SystemExit("Serbia not found in world")
if kosovo_geom is None:
    raise SystemExit("Kosovo not found")

merged = unary_union([serbia_geom, kosovo_geom])
print(f"World Serbia area {serbia_geom.area:.4f}, Kosovo {kosovo_geom.area:.4f}, merged {merged.area:.4f}")
print(f"Merged bounds {merged.bounds}")

out = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Serbia", "shapeName": "Serbia", "UN": True},
            "geometry": mapping(merged)
        }
    ]
}
out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out_path}")
