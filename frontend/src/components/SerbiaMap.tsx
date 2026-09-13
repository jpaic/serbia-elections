"use client";

import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import type { Feature, Geometry } from "geojson";
import {
  NO_DATA_COLOR,
  tieredLeaderFill,
  getTier,
  stripePatternId,
} from "@/lib/colorScale";
import type { MunicipalityRow, RegionResult } from "@/lib/types";
import opstinaRegionMap from "../../public/data/opstina-region-map.json";

const GEO_REGIONI = "/data/serbia-regioni.geojson";
const GEO_OPSTINE = "/data/serbia-opstine-detailed.geojson";

const DEFAULT_CENTER: [number, number] = [20.95, 44.05];
const DEFAULT_SCALE = 4200;
const REGION_SCALE: Record<string, number> = {
  "Београдски регион": 15000,
  "Регион Војводине": 5200,
  "Регион Шумадије и Западне Србије": 4800,
  "Регион Јужне и Источне Србије": 4600,
  "Регион Косово и Метохија": 7500,
};

type RSMFeature = Feature<Geometry> & { rsmKey: string; svgPath: string };
function nameOf(f: RSMFeature): string {
  return (f.properties as { name?: string } | null)?.name ?? "";
}
function shapeNameOf(f: RSMFeature): string {
  const p = f.properties as Record<string, unknown> | null;
  return (p?.["shapeName"] as string) || (p?.["name"] as string) || "";
}
function normalize(name: string): string {
  return name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/city|municipality|opstina|gradska opstina/g, "").replace(/[^a-z]/g, "").trim();
}
const OPSTINA_TO_REGION = opstinaRegionMap as Record<string, string>;

export default function SerbiaMap({
  regions,
  municipalities,
  onSelectRegion,
  selectedRegion,
  selectedMunicipalityId,
  onSelectMunicipality,
}: {
  regions: RegionResult[];
  municipalities?: MunicipalityRow[];
  onSelectRegion: (regionName: string | null) => void;
  selectedRegion: string | null;
  selectedMunicipalityId?: number | null;
  onSelectMunicipality?: (id: number | null) => void;
}) {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const [hoveredOpstina, setHoveredOpstina] = useState<string | null>(null);
  const [selectedGeo, setSelectedGeo] = useState<RSMFeature | null>(null);
  const [regionGeos, setRegionGeos] = useState<RSMFeature[]>([]);

  const isLocked = !!selectedRegion;

  const regionByName = useMemo(() => {
    const m = new Map<string, RegionResult>();
    for (const r of regions) m.set(r.region, r);
    return m;
  }, [regions]);

  const munByNorm = useMemo(() => {
    const m = new Map<string, MunicipalityRow>();
    if (!municipalities) return m;
    for (const mun of municipalities) {
      const k = normalize(mun.name);
      if (!m.has(k)) m.set(k, mun);
      m.set(mun.name.toLowerCase(), mun);
      m.set(String(mun.id), mun);
    }
    return m;
  }, [municipalities]);

  // Za selektovanu opštinu na mapi - nađi njen shapeName
  const selectedOpstinaShape = useMemo(() => {
    if (!selectedMunicipalityId || !municipalities) return null;
    const mun = municipalities.find((x) => x.id === selectedMunicipalityId);
    if (!mun) return null;
    const norm = normalize(mun.name);
    // nađi shapeName koji mapira na ovu opštinu
    for (const [shape, region] of Object.entries(OPSTINA_TO_REGION)) {
      if (region !== selectedRegion) continue;
      if (normalize(shape) === norm) return shape;
    }
    return null;
  }, [selectedMunicipalityId, municipalities, selectedRegion]);

  const tossupColors = useMemo(() => {
    const s = new Set<string>();
    for (const r of regions) if (r.leader && getTier(r.margin_pct, true) === "tossup" && r.leader.color_hex) s.add(r.leader.color_hex);
    if (municipalities) for (const m of municipalities) if (m.leader && getTier(m.margin_pct, true) === "tossup" && m.leader.color_hex) s.add(m.leader.color_hex);
    return Array.from(s);
  }, [regions, municipalities]);

  useEffect(() => {
    if (!selectedRegion) { setSelectedGeo(null); return; }
    if (selectedGeo && nameOf(selectedGeo) === selectedRegion) return;
    const g = regionGeos.find((x) => nameOf(x) === selectedRegion);
    if (g) setSelectedGeo(g);
  }, [selectedRegion, regionGeos]);

  const projectionConfig = useMemo(() => {
    if (isLocked && selectedGeo) {
      const props = selectedGeo.properties as Record<string, unknown> | null;
      const centroid = props?.["centroid"] as [number, number] | undefined;
      const scale = (selectedGeo && REGION_SCALE[nameOf(selectedGeo)]) || 9000;
      if (centroid && Array.isArray(centroid) && centroid.length === 2) return { center: centroid as [number, number], scale };
    }
    return { center: DEFAULT_CENTER, scale: DEFAULT_SCALE };
  }, [isLocked, selectedGeo]);

  function handleRegionClick(g: RSMFeature) {
    const n = nameOf(g);
    if (selectedRegion === n) { setSelectedGeo(null); onSelectRegion(null); return; }
    setSelectedGeo(g);
    onSelectRegion(n);
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#0b0d12]">
      <ComposableMap projection="geoMercator" projectionConfig={projectionConfig} style={{ width: "100%", height: "100%" }}>
        <defs>
          {tossupColors.map((c) => (
            <pattern key={c} id={stripePatternId(c)} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width={8} height={8} fill="#1e232e" />
              <rect width={4} height={8} fill={c} opacity={0.55} />
            </pattern>
          ))}
        </defs>

        {/* Kada nije zumirano - prikaži 5 regiona */}
        {!isLocked && (
          <Geographies geography={GEO_REGIONI}>
            {({ geographies }) => {
              if (geographies.length && regionGeos.length === 0) setTimeout(() => setRegionGeos(geographies as RSMFeature[]), 0);
              return geographies.map((geo) => {
                const g = geo as RSMFeature;
                const name = nameOf(g);
                const data = regionByName.get(name);
                const hov = hoveredRegion === name;
                const fill = (() => {
                  if (!data?.leader) return NO_DATA_COLOR;
                  const t = getTier(data.margin_pct, true);
                  if (t === "tossup") return `url(#${stripePatternId(data.leader.color_hex)})`;
                  return tieredLeaderFill(data.leader.color_hex, data.margin_pct);
                })();
                return (
                  <Geography
                    key={g.rsmKey}
                    geography={g}
                    onMouseEnter={() => setHoveredRegion(name)}
                    onMouseLeave={() => setHoveredRegion(null)}
                    onClick={() => handleRegionClick(g)}
                    fill={fill}
                    stroke="#0a0c10"
                    strokeWidth={1.0}
                    opacity={hov ? 1 : 0.97}
                    style={{ cursor: "pointer", outline: "none" }}
                  />
                );
              });
            }}
          </Geographies>
        )}

        {/* Kad je zumirano - samo okvir regiona + opštine */}
        {isLocked && selectedGeo && (
          <>
            <Geographies geography={GEO_REGIONI}>
              {() => (
                <Geography
                  key={selectedGeo.rsmKey + "-frame"}
                  geography={selectedGeo}
                  fill="none"
                  stroke="rgba(255,255,255,0.25)"
                  strokeWidth={1.8}
                  style={{ pointerEvents: "none", outline: "none" }}
                />
              )}
            </Geographies>
            <Geographies geography={GEO_OPSTINE}>
              {({ geographies }) => {
                const geos = geographies as RSMFeature[];
                const filtered = geos.filter((op) => OPSTINA_TO_REGION[shapeNameOf(op)] === selectedRegion);
                if (filtered.length === 0) return null;
                return filtered.map((op) => {
                  const sName = shapeNameOf(op);
                  const mun = munByNorm.get(normalize(sName)) || munByNorm.get(sName.toLowerCase());
                  const isSelectedOpstina = selectedOpstinaShape ? normalize(sName) === normalize(selectedOpstinaShape) : false;
                  const hov = hoveredOpstina === op.rsmKey;
                  const fill = (() => {
                    if (!mun?.leader) return "rgba(42,48,62,0.45)";
                    const t = getTier(mun.margin_pct, true);
                    if (t === "tossup") return `url(#${stripePatternId(mun.leader.color_hex)})`;
                    return tieredLeaderFill(mun.leader.color_hex, mun.margin_pct);
                  })();
                  const hasData = !!mun?.leader;
                  return (
                    <Geography
                      key={op.rsmKey}
                      geography={op}
                      onMouseEnter={() => setHoveredOpstina(op.rsmKey)}
                      onMouseLeave={() => setHoveredOpstina(null)}
                      onClick={() => {
                        if (!mun) return;
                        onSelectMunicipality?.(mun.id === selectedMunicipalityId ? null : mun.id);
                      }}
                      fill={fill}
                      stroke={isSelectedOpstina ? "#ffffff" : hov ? "#ffffff" : hasData ? "#f1f5f9" : "rgba(241,245,249,0.5)"}
                      strokeWidth={isSelectedOpstina ? 2.2 : hov ? 1.6 : 1.0}
                      opacity={isSelectedOpstina ? 1 : hov ? 1 : hasData ? 0.92 : 0.5}
                      style={{ cursor: mun ? "pointer" : "default", outline: "none" }}
                    />
                  );
                });
              }}
            </Geographies>
          </>
        )}
      </ComposableMap>

      {isLocked && (
        <button onClick={() => { setSelectedGeo(null); onSelectRegion(null); }} className="absolute top-3 left-3 rounded-full bg-black/70 backdrop-blur px-3.5 py-1.5 text-xs font-medium text-white border border-white/15 hover:bg-black/85 shadow-lg">
          ← Svi regioni
        </button>
      )}

      <div className="absolute bottom-3 right-3 rounded-xl bg-black/70 backdrop-blur border border-white/10 px-3 py-2 hidden sm:flex items-center gap-3">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30] border border-white/20" /><span className="text-[10px] text-white/70">Sigurno ≥10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30]/60 border border-white/20" /><span className="text-[10px] text-white/70">Umereno 5–10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-white/20" style={{ background: `repeating-linear-gradient(45deg, #1e232e 0 3px, #D85A30 3px 6px)` }} /><span className="text-[10px] text-white/70">Neizvesno &lt;5%</span></span>
      </div>

      {!isLocked && hoveredRegion && (() => {
        const d = regionByName.get(hoveredRegion);
        if (!d) return null;
        const tier = getTier(d.margin_pct, !!d.leader);
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 right-3 sm:right-auto sm:min-w-[260px] rounded-xl bg-black/80 backdrop-blur border border-white/10 px-4 py-3 shadow-xl">
            <p className="text-sm font-semibold text-white mb-1">{d.region}</p>
            {d.leader ? (
              <>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: d.leader.color_hex || "#888" }} />
                  <span className="text-xs text-white/90">{d.leader.short_name || d.leader.name}</span>
                  <span className="text-xs font-semibold text-white ml-auto tabular-nums">{d.leader.pct.toFixed(1)}%</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ml-1 ${tier === "secure" ? "bg-white/15 text-white border-white/20" : tier === "lean" ? "bg-white/10 text-white/80 border-white/15" : "bg-amber-500/20 text-amber-300 border-amber-500/30"}`}>{tier === "secure" ? "SIGURNO" : tier === "lean" ? "UMERENO" : "NEIZVESNO"}</span>
                </div>
                <div className="flex gap-3 text-[11px] text-white/50 tabular-nums">
                  <span>{d.processed_stations}/{d.total_stations} BM · {d.processed_pct.toFixed(0)}% obrađeno</span>
                  <span>· {d.turnout_pct.toFixed(1)}% izlaznost</span>
                  <span>· +{d.margin_pct.toFixed(1)}pp</span>
                </div>
              </>
            ) : <p className="text-xs text-white/50">Nema još obrađenih rezultata</p>}
          </div>
        );
      })()}

      {isLocked && (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/60 backdrop-blur border border-white/10 px-3 py-2">
          <p className="text-[11px] text-white/70">Opštine u regionu — klik na opštinu za detalje</p>
        </div>
      )}
    </div>
  );
}
