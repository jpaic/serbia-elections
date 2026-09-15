"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from "react-simple-maps";
import { api } from "@/lib/api";
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
  electionStatus,
  electionId,
}: {
  diasporaRegion?: RegionResult | null;
  onSelectStation?: (id: number | null) => void;
  selectedStationId?: number | null;
  electionStatus?: string;
  electionId?: number | null;
}) {
  const verb = electionStatus === "closed" ? "pobedio" : "vodi";
  const [hovered, setHovered] = useState<number | null>(null);
  // Kontrolisana pozicija: i centar i zum se vode iz eventa, inače
  // ZoomableGroup pri svakom re-renderu vrati mapu na fiksni centar (drift).
  const [position, setPosition] = useState<{ coordinates: [number, number]; zoom: number }>({
    coordinates: [15, 38],
    zoom: 1,
  });

  const leaderColor = diasporaRegion?.leader?.color_hex || "#3b82d6";
  const isTossup = diasporaRegion ? diasporaRegion.margin_pct < 5 : false;

  // Pobednik svake ambasade ponaosob (boja tačke = ko je tu osvojio)
  const { data: stationResults } = useSWR(
    electionId ? ["diaspora", electionId] : null,
    () => api.diaspora(electionId!),
    { refreshInterval: 30000 }
  );
  const leaderByStation = useMemo(() => {
    const m = new Map<number, { color: string | null; short: string; pct: number; votes: number }>();
    for (const r of stationResults ?? []) {
      m.set(r.rik_station_id, { color: r.color_hex, short: r.short_name, pct: r.pct, votes: r.votes });
    }
    return m;
  }, [stationResults]);
  // Kontra-skaliranje da tačke zadrže istu veličinu na ekranu pri zoomu.
  const r = (base: number) => base / position.zoom;
  const handleMove = ({ coordinates, zoom: z }: { coordinates?: [number, number]; zoom?: number }) => {
    setPosition((prev) => ({
      coordinates: coordinates ?? prev.coordinates,
      zoom: typeof z === "number" ? z : prev.zoom,
    }));
  };

  return (
    <div className="relative w-full h-full bg-[#080a0f] overflow-hidden">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 145, center: [15, 38] }}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup
          center={position.coordinates}
          zoom={position.zoom}
          minZoom={1}
          maxZoom={6}
          translateExtent={[
            [-180, -90],
            [1000, 600],
          ]}
          onMove={handleMove}
          onMoveEnd={handleMove}
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
            // Boja tačke = pobednik TE ambasade; bez podataka neutralno siva
            const node = leaderByStation.get(s.id);
            const dotColor = node?.color || "#2a2f3a";
            return (
              <Marker key={s.id} coordinates={[s.lon, s.lat]}>
                <g
                  onMouseEnter={() => setHovered(s.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelectStation?.(isSelected ? null : s.id)}
                  style={{ cursor: "pointer" }}
                >
                  {/* halo za hover/selected - kontra-skalirano */}
                  {(isHovered || isSelected) && (
                    <circle r={r(isSelected ? 10 : 8)} fill={dotColor} opacity={0.25} />
                  )}
                  {/* spoljni prsten za tossup */}
                  {isToss && node ? (
                    <>
                      <circle r={r(isSelected ? 5.5 : 4.5)} fill="#1e232e" stroke={dotColor} strokeWidth={r(1.2)} />
                      <circle r={r(isSelected ? 3 : 2.2)} fill={dotColor} opacity={0.9} />
                    </>
                  ) : (
                    <circle
                      r={r(isSelected ? 5.5 : 4.2)}
                      fill={dotColor}
                      stroke={isSelected || isHovered ? "#fff" : "rgba(0,0,0,0.5)"}
                      strokeWidth={r(isSelected || isHovered ? 1.2 : 0.6)}
                      opacity={node ? 0.95 : 0.7}
                    />
                  )}
                  {isHovered && <circle r={r(6)} fill="none" stroke={dotColor} strokeWidth={r(0.8)} opacity={0.5} />}
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
          Dijaspora {diasporaRegion?.leader ? `· ${diasporaRegion.leader.short_name} ${verb} ${diasporaRegion.leader.pct.toFixed(1)}%` : "· nema podataka"}
        </span>
        <span className="text-[10px] text-white/30 ml-2">{(diasporaStations as DiasporaStation[]).length} biračkih mesta</span>
      </div>

      {/* Hover tooltip */}
      {hovered && (() => {
        const s = (diasporaStations as DiasporaStation[]).find((x) => x.id === hovered);
        if (!s) return null;
        const node = leaderByStation.get(s.id);
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/80 backdrop-blur border border-white/10 px-3 py-2 shadow-xl">
            <p className="text-xs font-medium text-white">{s.city} · {s.country}</p>
            <p className="text-[11px] text-white/60 truncate max-w-[260px]">{s.name}</p>
            {node ? (
              <p className="text-[11px] text-white/70 mt-1 tabular-nums">
                {node.short} {node.pct.toFixed(1)}% · {node.votes.toLocaleString("sr-RS")} glasova
              </p>
            ) : diasporaRegion?.leader ? (
              <p className="text-[11px] text-white/40 mt-1">
                Ukupno dijaspora: {diasporaRegion.leader.short_name} {diasporaRegion.leader.pct.toFixed(1)}%
              </p>
            ) : null}
          </div>
        );
      })()}
    </div>
  );
}
