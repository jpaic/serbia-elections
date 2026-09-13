"use client";

import { useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from "react-simple-maps";
import type { RegionResult } from "@/lib/types";

const WORLD_GEO = "/data/world.geojson";
const SERBIA_UN_GEO = "/data/serbia-world-un.geojson";

// Staticka lista ambasada sa koordinatama (generisano iz RIK 2023 region 101)
import diasporaStations from "../../public/data/diaspora-stations.json";

type DiasporaStation = {
  id: number;
  name: string;
  city: string;
  country: string;
  lat: number;
  lon: number;
};

export default function WorldMap({
  diasporaRegion,
  onSelectStation,
  selectedStationId,
}: {
  diasporaRegion?: RegionResult | null;
  onSelectStation?: (id: number | null) => void;
  selectedStationId?: number | null;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);

  const leaderColor = diasporaRegion?.leader?.color_hex || "#3b82d6";
  const isTossup = diasporaRegion ? diasporaRegion.margin_pct < 5 : false;
  // da krugovi ostanu iste veličine na ekranu pri zoomu: radius / zoom
  const r = (base: number) => base / zoom;

  // Grupiši po državi za tooltip count
  const byCountry = useMemo(() => {
    const m = new Map<string, number>();
    for (const s of diasporaStations as DiasporaStation[]) {
      m.set(s.country, (m.get(s.country) || 0) + 1);
    }
    return m;
  }, []);

  return (
    <div className="relative w-full h-full bg-[#080a0f] overflow-hidden">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 145, center: [15, 38] }}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup
          center={[15, 38]}
          zoom={zoom}
          minZoom={1}
          maxZoom={6}
          translateExtent={[
            [-180, -90],
            [1000, 600],
          ]}
          onMoveEnd={({ zoom: z }) => {
            if (typeof z === "number") setZoom(z);
          }}
        >
          <Geographies geography={WORLD_GEO}>
            {({ geographies }) =>
              geographies
                .filter((geo) => {
                  const p = (geo as unknown as { properties: Record<string, unknown> }).properties as Record<string, unknown>;
                  const name = (p?.name as string) || (p?.NAME as string) || "";
                  // UN: Kosovo nije posebna država - filtriramo i staru Srbiju bez Kosova
                  if (name === "Kosovo" || name === "Kosovo*") return false;
                  if (name === "Republic of Serbia" || name === "Serbia") return false;
                  return true;
                })
                .map((geo) => (
                  <Geography
                    key={(geo as unknown as { rsmKey: string }).rsmKey}
                    geography={geo as never}
                    fill="#1a1f2a"
                    stroke="#0b0d12"
                    strokeWidth={0.4}
                    style={{ outline: "none" }}
                  />
                ))
            }
          </Geographies>

          {/* Srbija po UN - sa Kosovom kao deo Srbije */}
          <Geographies geography={SERBIA_UN_GEO}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={(geo as unknown as { rsmKey: string }).rsmKey}
                  geography={geo as never}
                  fill="#1a1f2a"
                  stroke="#0b0d12"
                  strokeWidth={0.5}
                  style={{ outline: "none" }}
                />
              ))
            }
          </Geographies>

          {(diasporaStations as DiasporaStation[]).map((s) => {
            const isSelected = selectedStationId === s.id;
            const isHovered = hovered === s.id;
            const isToss = isTossup;
            return (
              <Marker key={s.id} coordinates={[s.lon, s.lat]}>
                <g
                  onMouseEnter={() => setHovered(s.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelectStation?.(isSelected ? null : s.id)}
                  style={{ cursor: "pointer" }}
                >
                  {/* halo za hover/selected - proporcionalno */}
                  {(isHovered || isSelected) && (
                    <circle r={r(isSelected ? 10 : 8)} fill={leaderColor} opacity={0.18} />
                  )}
                  {/* spoljni prsten za tossup */}
                  {isToss ? (
                    <>
                      <circle r={r(isSelected ? 5.5 : 4.5)} fill="#1e232e" stroke={leaderColor} strokeWidth={r(1.2)} />
                      <circle r={r(isSelected ? 3 : 2.2)} fill={leaderColor} opacity={0.9} />
                    </>
                  ) : (
                    <circle
                      r={r(isSelected ? 5.5 : 4.2)}
                      fill={leaderColor}
                      stroke={isSelected ? "#fff" : "rgba(0,0,0,0.5)"}
                      strokeWidth={r(isSelected ? 1.2 : 0.6)}
                      opacity={0.92}
                    />
                  )}
                  {isHovered && <circle r={r(6)} fill="none" stroke={leaderColor} strokeWidth={r(0.8)} opacity={0.5} />}
                </g>
              </Marker>
            );
          })}
        </ZoomableGroup>
      </ComposableMap>

      {/* Legenda */}
      <div className="absolute bottom-3 right-3 rounded-xl bg-black/70 backdrop-blur border border-white/10 px-3 py-2 flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: leaderColor }} />
        <span className="text-[11px] text-white/70">
          Dijaspora {diasporaRegion?.leader ? `· ${diasporaRegion.leader.short_name} vodi ${diasporaRegion.leader.pct.toFixed(1)}%` : "· nema podataka"}
        </span>
        <span className="text-[10px] text-white/30 ml-2">{(diasporaStations as DiasporaStation[]).length} biračkih mesta</span>
      </div>

      {/* Hover tooltip */}
      {hovered && (() => {
        const s = (diasporaStations as DiasporaStation[]).find((x) => x.id === hovered);
        if (!s) return null;
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/80 backdrop-blur border border-white/10 px-3 py-2 shadow-xl">
            <p className="text-xs font-medium text-white">{s.city} · {s.country}</p>
            <p className="text-[11px] text-white/60 truncate max-w-[260px]">{s.name}</p>
            {diasporaRegion?.leader && (
              <p className="text-[11px] text-white/40 mt-1">
                Ukupno dijaspora: {diasporaRegion.leader.short_name} {diasporaRegion.leader.pct.toFixed(1)}% (margina +{diasporaRegion.margin_pct.toFixed(1)}pp)
              </p>
            )}
          </div>
        );
      })()}
    </div>
  );
}
