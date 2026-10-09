"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FeatureCollection, GeoJsonProperties } from "geojson";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { interpolateRgb } from "d3-interpolate";
import { scaleLinear } from "d3-scale";
import { feature } from "topojson-client";
import { getTier } from "@/lib/colorScale";
import { isDiasporaRegion, isZavodiRegion } from "@/lib/display";

const MAP_WIDTH = 800;
const MAP_HEIGHT = 600;

type RegionData = {
  region: string;
  leader: { short_name: string; color_hex: string; pct: number } | null;
  margin_pct: number;
  processed_pct: number;
  total_stations: number;
  processed_stations: number;
  centroid?: [number, number];
};

type SimulationMapProps = {
  regions: RegionData[];
  selectedRegion: string | null;
  onSelectRegion: (region: string) => void;
  animationProgress: number;
  isRunning: boolean;
};

export default function SimulationMap({
  regions,
  selectedRegion,
  onSelectRegion,
  animationProgress,
  isRunning,
}: SimulationMapProps) {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const progressRef = useRef(animationProgress);

  useEffect(() => {
    progressRef.current = animationProgress;
  }, [animationProgress]);

  const validRegions = useMemo(
    () => regions.filter((r) => !isDiasporaRegion(r.region) && !isZavodiRegion(r.region)),
    [regions]
  );

  const maxStations = useMemo(
    () => Math.max(...validRegions.map((r) => r.total_stations), 1),
    [validRegions]
  );

  const getRegionColor = (regionData: RegionData, progress: number) => {
    if (!regionData.leader) return "#1a1d26";

    const baseColor = regionData.leader.color_hex || "#888";
    const stationProgress = Math.min(
      progress * regionData.total_stations / maxStations,
      1
    );
    const colorProgress = Math.min(stationProgress * 1.5, 1);

    const dark = interpolateRgb("#0b0d12", baseColor)(colorProgress);
    return dark;
  };

  const getFillOpacity = (regionData: RegionData, progress: number) => {
    if (!regionData.leader) return 0.15;
    const stationProgress = Math.min(
      progress * regionData.total_stations / maxStations,
      1
    );
    return 0.15 + stationProgress * 0.85;
  };

  const getStrokeColor = (regionData: RegionData) => {
    if (regionData.region === selectedRegion) return "white";
    if (regionData.region === hoveredRegion) return "white/60";
    return "white/15";
  };

  const getStrokeWidth = (regionData: RegionData) => {
    if (regionData.region === selectedRegion) return 2.5;
    if (regionData.region === hoveredRegion) return 1.5;
    return 0.5;
  };

  const mapRef = useRef<SVGSVGElement>(null);
  const [projection, setProjection] = useState<{
    scale: number;
    x: number;
    y: number;
  } | null>(null);

  return (
    <div className="relative w-full h-full min-h-0 flex flex-col">
      <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="w-48 h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500 transition-all duration-300"
              style={{ width: `${animationProgress * 100}%` }}
            />
          </div>
          <span className="text-xs text-white/60 font-mono tabular-nums">
            {Math.round(animationProgress * 100)}%
          </span>
          <span className="text-xs text-white/40 px-2 py-0.5 rounded bg-white/5">
            {isRunning ? "U TOKU" : "PAUZA"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-white/40">Brzina:</span>
          <select
            className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-white outline-none"
            defaultValue="1"
          >
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
          </select>
        </div>
      </div>

      <div className="flex-1 relative">
        <ComposableMap
          ref={mapRef}
          projection="geoMercator"
          projectionConfig={{
            center: [20.5, 44.2],
            scale: 1400,
          }}
          width={MAP_WIDTH}
          height={MAP_HEIGHT}
          style={{ width: "100%", height: "100%", touchAction: "none" }}
        >
<Geographies geography="/srbia-okruzi.topojson">
            {({ geographies }) =>
              geographies.map((geo) => {
                const regionName = geo.properties?.name_sr || geo.properties?.name || "";
                const regionData = validRegions.find((r) => r.region === regionName);
                const progress = progressRef.current;

                if (!regionData) {
                  const emptyStyle = {
                    default: { fill: "#1a1d26", fillOpacity: 0.15, stroke: "white/15", strokeWidth: 0.5 },
                    hover: { fill: "#1a1d26", fillOpacity: 0.25, stroke: "white/80", strokeWidth: 1.5 },
                    pressed: { fill: "#1a1d26", fillOpacity: 0.15, stroke: "white", strokeWidth: 2 },
                  } as any;
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      style={emptyStyle}
                    />
                  );
                }

                const regionStyle = {
                      default: {
                        fill: getRegionColor(regionData, progress),
                        fillOpacity: getFillOpacity(regionData, progress),
                        stroke: getStrokeColor(regionData),
                        strokeWidth: getStrokeWidth(regionData),
                        transition: "fill 300ms ease, fill-opacity 300ms ease, stroke 150ms ease",
                      },
                      hover: {
                        fill: getRegionColor(regionData, progress),
                        fillOpacity: Math.min(getFillOpacity(regionData, progress) + 0.1, 1),
                        stroke: "white/80",
                        strokeWidth: 1.5,
                      },
                      pressed: {
                        fill: getRegionColor(regionData, progress),
                        fillOpacity: getFillOpacity(regionData, progress),
                        stroke: "white",
                        strokeWidth: 2,
                      },
                    } as any;

                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={() => onSelectRegion(regionData.region)}
                        onMouseEnter={() => setHoveredRegion(regionData.region)}
                        onMouseLeave={() => setHoveredRegion(null)}
                        style={regionStyle}
                      />
                    );
              })}
            </Geographies>

          <svg className="absolute inset-0 pointer-events-none" style={{ overflow: "visible" }}>
            {validRegions.map((regionData) => {
              if (!regionData.leader) return null;

              const centroid = regionData.centroid;
              if (!centroid) return null;

              return (
                <g
                  key={regionData.region}
                  className="transition-opacity duration-300"
                  style={{
                    opacity: animationProgress > 0.1 ? 1 : 0,
                    transform: `translate(${centroid[0]}px, ${centroid[1]}px)`,
                  }}
                >
                  <circle
                    r={6 + 10 * animationProgress}
                    fill={regionData.leader.color_hex}
                    fillOpacity={0.2}
                    stroke={regionData.leader.color_hex}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    style={{ animation: "pulse 2s ease-in-out infinite" }}
                  />
                  <circle
                    r={4}
                    fill={regionData.leader.color_hex}
                    stroke="white"
                    strokeWidth={1}
                  />
                  <text
                    x={0}
                    y={-12}
                    textAnchor="middle"
                    fill="white"
                    fontSize="9"
                    fontWeight="600"
                    style={{ pointerEvents: "none", textShadow: "0 0 3px #000" }}
                  >
                    {regionData.leader.short_name}
                  </text>
                  <text
                    x={0}
                    y={0}
                    textAnchor="middle"
                    fill="white/70"
                    fontSize="8"
                    style={{ pointerEvents: "none", textShadow: "0 0 3px #000" }}
                  >
                    {regionData.leader.pct.toFixed(1)}%
                  </text>
                </g>
              );
            })}
            <style jsx global>{`
              @keyframes pulse {
                0%, 100% { r: 8; opacity: 0.3; }
                50% { r: 18; opacity: 0.1; }
              }
            `}</style>
          </svg>
        </ComposableMap>

        <div className="absolute bottom-4 left-4 right-4 flex flex-wrap justify-center gap-2 z-10">
          <Legend />
        </div>
      </div>
    </div>
  );
}

function Legend() {
const tiers = [
    { label: "SIGURNO (≥10%)", color: "bg-emerald-500/80" },
    { label: "UMERENO (5–10%)", color: "bg-amber-500/80" },
    { label: "NEIZVESNO (<5%)", color: "bg-white/80" },
    { label: "Nema podataka", color: "bg-white/10" },
  ];

  const tierItems = tiers.map((t, i) => {
    return (
      <span key={i} className="flex items-center gap-1.5">
        <span className={`w-3 h-1.5 rounded ${t.color}`} />
        <span className="text-white/70">{t.label}</span>
      </span>
    );
  });

  return (
    <div className="flex flex-wrap items-center gap-2 px-3 py-2 bg-[#0e1117]/90 backdrop-blur rounded-lg border border-white/10 text-[10px]">
      {tierItems}
    </div>
  );
}