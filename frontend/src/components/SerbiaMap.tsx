"use client";

import { useMemo, useState } from "react";
import { geoCentroid } from "d3-geo";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import type { Feature, Geometry } from "geojson";
import { leaderColor, NO_DATA_COLOR } from "@/lib/colorScale";
import type { RegionResult } from "@/lib/types";

const GEO_URL = "/data/serbia-okruzi.geojson";
const DEFAULT_CENTER: [number, number] = [20.9, 44.2];
const DEFAULT_ZOOM = 1;

// react-simple-maps predaje geografiju kao GeoJSON Feature + rsmKey. Definišemo
// sopstveni minimalni tip da izbegnemo sukob imena sa `Geography` komponentom
// koju biblioteka izvozi iz istog modula.
type GeographyFeature = Feature<Geometry> & { rsmKey: string };

export default function SerbiaMap({
  regions,
  onSelectRegion,
  selectedRegion,
}: {
  regions: RegionResult[];
  onSelectRegion: (regionName: string | null) => void;
  selectedRegion: string | null;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

  const regionByName = useMemo(() => {
    const map = new Map<string, RegionResult>();
    for (const r of regions) map.set(r.region, r);
    return map;
  }, [regions]);

  const hoveredData = hovered ? regionByName.get(hovered) : null;

  function nameOf(geo: GeographyFeature): string {
    return (geo.properties as { name?: string } | null)?.name ?? "";
  }

  function handleClick(geo: GeographyFeature) {
    const name = nameOf(geo);
    if (selectedRegion === name) {
      // drugi klik na isti okrug -> izlazi iz zuma
      setCenter(DEFAULT_CENTER);
      setZoom(DEFAULT_ZOOM);
      onSelectRegion(null);
      return;
    }
    const centroid = geoCentroid(geo);
    if (centroid && Number.isFinite(centroid[0]) && Number.isFinite(centroid[1])) {
      setCenter(centroid as [number, number]);
      setZoom(4.2);
    }
    onSelectRegion(name);
  }

  function resetZoom() {
    setCenter(DEFAULT_CENTER);
    setZoom(DEFAULT_ZOOM);
    onSelectRegion(null);
  }

  return (
    <div className="relative w-full h-full">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ center: DEFAULT_CENTER, scale: 3200 }}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup
          center={center}
          zoom={zoom}
          minZoom={1}
          maxZoom={8}
          onMoveEnd={({ coordinates, zoom: z }) => {
            if (coordinates) setCenter(coordinates as [number, number]);
            if (typeof z === "number") setZoom(z);
          }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const name = nameOf(geo);
                const data = regionByName.get(name);
                const isSelected = selectedRegion === name;
                const isHovered = hovered === name;
                const fill = data
                  ? leaderColor(data.leader?.color_hex, data.margin_pct)
                  : NO_DATA_COLOR;
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={() => setHovered(name)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => handleClick(geo)}
                    fill={fill}
                    stroke={isSelected ? "#f5f6f8" : "#0a0c10"}
                    strokeWidth={isSelected ? 1.4 : 0.6 / zoom}
                    opacity={isHovered ? 1 : 0.96}
                    style={{ cursor: "pointer", outline: "none" }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {zoom > DEFAULT_ZOOM && (
        <button
          onClick={resetZoom}
          className="absolute top-3 left-3 rounded-full bg-black/60 backdrop-blur px-3 py-1.5 text-xs font-medium text-white/90 border border-white/10 hover:bg-black/80 transition-colors"
        >
          ← Cela Srbija
        </button>
      )}

      {hoveredData && (
        <div className="pointer-events-none absolute bottom-3 left-3 right-3 sm:right-auto sm:min-w-[220px] rounded-xl bg-black/75 backdrop-blur border border-white/10 px-4 py-3 shadow-xl">
          <p className="text-sm font-semibold text-white mb-1">{hoveredData.region}</p>
          {hoveredData.leader ? (
            <div className="flex items-center gap-2 mb-1">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                style={{ background: hoveredData.leader.color_hex || "#888" }}
              />
              <span className="text-xs text-white/90">
                {hoveredData.leader.short_name || hoveredData.leader.name}
              </span>
              <span className="text-xs font-semibold text-white ml-auto tabular-nums">
                {hoveredData.leader.pct.toFixed(1)}%
              </span>
            </div>
          ) : (
            <p className="text-xs text-white/50 mb-1">Nema još obrađenih rezultata</p>
          )}
          <p className="text-[11px] text-white/50 tabular-nums">
            {hoveredData.processed_stations}/{hoveredData.total_stations} biračkih mesta ·{" "}
            {hoveredData.processed_pct.toFixed(0)}% obrađeno
          </p>
        </div>
      )}
    </div>
  );
}
