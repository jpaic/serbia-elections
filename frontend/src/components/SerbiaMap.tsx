"use client";

import { useEffect, useMemo, useState } from "react";
import { geoCentroid, geoContains } from "d3-geo";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
} from "react-simple-maps";
import type { Feature, Geometry } from "geojson";
import {
  NO_DATA_COLOR,
  tieredLeaderFill,
  getTier,
  stripePatternId,
} from "@/lib/colorScale";
import type { MunicipalityRow, RegionResult } from "@/lib/types";

const GEO_OKRUZI = "/data/serbia-okruzi.geojson";
const GEO_OPSTINE = "/data/serbia-opstine.geojson";

// Veći default zoom da nema praznog prostora - skala 4200 umesto 3200, centar blago korigovan
const DEFAULT_CENTER: [number, number] = [20.95, 44.05];
const DEFAULT_ZOOM = 1.25;
const SELECTED_ZOOM = 4.6;
const MAP_SCALE = 4200;

// Clamp granice Srbije (lon/lat) da ne može da se odvuče u nedogled
const SERBIA_BOUNDS = {
  lonMin: 18.5,
  lonMax: 23.2,
  latMin: 41.6,
  latMax: 46.4,
};

function clampLonLat([lon, lat]: [number, number]): [number, number] {
  return [
    Math.max(SERBIA_BOUNDS.lonMin, Math.min(SERBIA_BOUNDS.lonMax, lon)),
    Math.max(SERBIA_BOUNDS.latMin, Math.min(SERBIA_BOUNDS.latMax, lat)),
  ];
}

type GeographyFeature = Feature<Geometry> & { rsmKey: string; svgPath: string };

function nameOf(geo: GeographyFeature): string {
  return (geo.properties as { name?: string } | null)?.name ?? "";
}

function opstinaNameOf(geo: GeographyFeature): string {
  // geoBoundaries ADM2: shapeName
  const p = geo.properties as Record<string, unknown> | null;
  return (p?.["shapeName"] as string) || (p?.["name"] as string) || "";
}

function normalizeOpstina(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/city|municipality|opstina|gradska opstina/g, "")
    .replace(/[^a-z]/g, "")
    .trim();
}

export default function SerbiaMap({
  regions,
  municipalities,
  onSelectRegion,
  selectedRegion,
}: {
  regions: RegionResult[];
  municipalities?: MunicipalityRow[];
  onSelectRegion: (regionName: string | null) => void;
  selectedRegion: string | null;
}) {
  const [hoveredOkrug, setHoveredOkrug] = useState<string | null>(null);
  const [hoveredOpstina, setHoveredOpstina] = useState<string | null>(null);
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const [okrugGeos, setOkrugGeos] = useState<GeographyFeature[]>([]);

  const isLocked = !!selectedRegion;

  const regionByName = useMemo(() => {
    const m = new Map<string, RegionResult>();
    for (const r of regions) m.set(r.region, r);
    return m;
  }, [regions]);

  const munByNormalized = useMemo(() => {
    const m = new Map<string, MunicipalityRow>();
    if (!municipalities) return m;
    for (const mun of municipalities) {
      const key = normalizeOpstina(mun.name);
      // ako postoji duplikat, zadrži prvi
      if (!m.has(key)) m.set(key, mun);
      // takođe mapiraj i puno ime za direktan match
      m.set(mun.name.toLowerCase(), mun);
    }
    return m;
  }, [municipalities]);

  // Kad se promeni selectedRegion spolja (npr. side panel), centriraj
  useEffect(() => {
    if (!selectedRegion) {
      setCenter(DEFAULT_CENTER);
      setZoom(DEFAULT_ZOOM);
      return;
    }
    const geo = okrugGeos.find((g) => nameOf(g) === selectedRegion);
    if (geo) {
      const c = geoCentroid(geo);
      if (c && Number.isFinite(c[0]) && Number.isFinite(c[1])) {
        setCenter(clampLonLat(c as [number, number]));
        setZoom(SELECTED_ZOOM);
      }
    }
  }, [selectedRegion, okrugGeos]);

  const hoveredOkrugData = hoveredOkrug ? regionByName.get(hoveredOkrug) : null;

  // Za pattern-e: sakupi boje lidera koji su tossup (<5%)
  const tossupColors = useMemo(() => {
    const set = new Set<string>();
    for (const r of regions) {
      if (r.leader && getTier(r.margin_pct, !!r.leader) === "tossup") {
        if (r.leader.color_hex) set.add(r.leader.color_hex);
      }
    }
    if (municipalities) {
      for (const m of municipalities) {
        if (m.leader && getTier(m.margin_pct, !!m.leader) === "tossup" && m.leader.color_hex) {
          set.add(m.leader.color_hex);
        }
      }
    }
    return Array.from(set);
  }, [regions, municipalities]);

  function handleOkrugClick(geo: GeographyFeature) {
    const name = nameOf(geo);
    if (selectedRegion === name) {
      onSelectRegion(null);
      return;
    }
    // ako je zaključano, dozvoli direktno prebacivanje na drugi okrug
    const c = geoCentroid(geo);
    if (c && Number.isFinite(c[0]) && Number.isFinite(c[1])) {
      setCenter(clampLonLat(c as [number, number]));
      setZoom(SELECTED_ZOOM);
    }
    onSelectRegion(name);
  }

  function handleReset() {
    onSelectRegion(null);
  }

  function fillForRegion(data: RegionResult | undefined): string {
    if (!data?.leader) return NO_DATA_COLOR;
    const tier = getTier(data.margin_pct, !!data.leader);
    if (tier === "tossup") return `url(#${stripePatternId(data.leader.color_hex)})`;
    return tieredLeaderFill(data.leader.color_hex, data.margin_pct);
  }

  function fillForMun(mun: MunicipalityRow | undefined): string {
    if (!mun?.leader) return "#1e232e";
    const tier = getTier(mun.margin_pct, !!mun.leader);
    if (tier === "tossup") return `url(#${stripePatternId(mun.leader.color_hex)})`;
    return tieredLeaderFill(mun.leader.color_hex, mun.margin_pct);
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#0b0d12]">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ center: DEFAULT_CENTER, scale: MAP_SCALE }}
        style={{ width: "100%", height: "100%" }}
      >
        {/* Dijagonalne šrafure za tossup */}
        <defs>
          {tossupColors.map((col) => (
            <pattern
              key={col}
              id={stripePatternId(col)}
              width={8}
              height={8}
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <rect width={8} height={8} fill="#1e232e" />
              <rect width={4} height={8} fill={col} opacity={0.55} />
            </pattern>
          ))}
        </defs>

        <ZoomableGroup
          center={center}
          zoom={zoom}
          minZoom={1}
          maxZoom={8}
          // Clamp + lock kad je okrug izabran
          translateExtent={[
            [-120, -80],
            [920, 520],
          ]}
          onMoveEnd={({ coordinates, zoom: z }) => {
            if (isLocked) return; // zaključano - ignoriši pan/zoom
            if (coordinates) {
              const clamped = clampLonLat(coordinates as [number, number]);
              setCenter(clamped);
            }
            if (typeof z === "number") setZoom(Math.max(1, Math.min(8, z)));
          }}
        >
          <Geographies geography={GEO_OKRUZI}>
            {({ geographies }) => {
              // sačuvaj za kasnije (centroid + contains)
              if (geographies.length && okrugGeos.length === 0) {
                // side-effect u renderu je ok za ovaj slučaj (jednokratno)
                setTimeout(() => setOkrugGeos(geographies as GeographyFeature[]), 0);
              }
              return geographies.map((geo) => {
                const g = geo as GeographyFeature;
                const name = nameOf(g);
                const data = regionByName.get(name);
                const isSelected = selectedRegion === name;
                const isHovered = hoveredOkrug === name;
                const isDimmed = isLocked && !isSelected;

                // Kad je zaključano a nije selektovano, prikaži bledo da ne ometa
                const fill = isDimmed ? "#151921" : fillForRegion(data);

                return (
                  <Geography
                    key={g.rsmKey}
                    geography={g}
                    onMouseEnter={() => !isLocked && setHoveredOkrug(name)}
                    onMouseLeave={() => setHoveredOkrug(null)}
                    onClick={() => handleOkrugClick(g)}
                    fill={fill}
                    stroke={isSelected ? "#f5f6f8" : isDimmed ? "#1a1f2a" : "#0a0c10"}
                    strokeWidth={isSelected ? 1.6 : isDimmed ? 0.3 : 0.7 / zoom}
                    opacity={isDimmed ? 0.35 : isHovered ? 1 : 0.97}
                    style={{
                      cursor: "pointer",
                      outline: "none",
                      transition: "opacity 0.2s, fill 0.3s",
                    }}
                  />
                );
              });
            }}
          </Geographies>

          {/* Opštine unutar izabranog okruga */}
          {isLocked && selectedRegion && (
            <Geographies geography={GEO_OPSTINE}>
              {({ geographies }) => {
                const selectedGeo = okrugGeos.find((g) => nameOf(g) === selectedRegion);
                if (!selectedGeo) return null;
                // Filtriraj opštine koje su unutar selektovanog okruga (centroid inside)
                const filtered = (geographies as GeographyFeature[]).filter((opGeo) => {
                  const centroid = geoCentroid(opGeo);
                  if (!centroid || !Number.isFinite(centroid[0])) return false;
                  try {
                    return geoContains(selectedGeo as unknown as Feature, centroid as [number, number]);
                  } catch {
                    return false;
                  }
                });

                // Ako nema poklapanja (npr. demo podaci), prikaži sve ali bledo - za debug
                const toRender = filtered.length > 0 ? filtered : [];

                return toRender.map((opGeo) => {
                  const shapeName = opstinaNameOf(opGeo);
                  const keyNorm = normalizeOpstina(shapeName);
                  const munData = munByNormalized.get(keyNorm) || munByNormalized.get(shapeName.toLowerCase());
                  const isHovered = hoveredOpstina === opGeo.rsmKey;
                  const fill = fillForMun(munData);

                  return (
                    <Geography
                      key={opGeo.rsmKey}
                      geography={opGeo}
                      onMouseEnter={() => setHoveredOpstina(opGeo.rsmKey)}
                      onMouseLeave={() => setHoveredOpstina(null)}
                      fill={fill}
                      stroke={isHovered ? "#ffffff" : "rgba(10,12,16,0.9)"}
                      strokeWidth={isHovered ? 1.1 : 0.45 / zoom}
                      opacity={isHovered ? 1 : 0.88}
                      style={{ cursor: "default", outline: "none" }}
                    />
                  );
                });
              }}
            </Geographies>
          )}
        </ZoomableGroup>
      </ComposableMap>

      {/* Dugme nazad - jedino mesto za izlaz iz zaključanog view-a */}
      {isLocked && (
        <button
          onClick={handleReset}
          className="absolute top-3 left-3 rounded-full bg-black/70 backdrop-blur px-3.5 py-1.5 text-xs font-medium text-white border border-white/15 hover:bg-black/85 transition-colors shadow-lg"
        >
          ← Svi okruzi
        </button>
      )}

      {/* Legenda za nijanse */}
      <div className="absolute bottom-3 right-3 rounded-xl bg-black/70 backdrop-blur border border-white/10 px-3 py-2 hidden sm:flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-[#D85A30] border border-white/20" />
          <span className="text-[10px] text-white/70">Sigurno ≥10%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-[#D85A30]/60 border border-white/20" />
          <span className="text-[10px] text-white/70">Umereno 5–10%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm border border-white/20"
            style={{
              background: `repeating-linear-gradient(45deg, #1e232e 0 3px, #D85A30 3px 6px)`,
            }}
          />
          <span className="text-[10px] text-white/70">Neizvesno &lt;5%</span>
        </div>
      </div>

      {/* Tooltip za okrug (samo kad nije zaključano) */}
      {!isLocked && hoveredOkrug && (() => {
        const d = regionByName.get(hoveredOkrug);
        if (!d) return null;
        const tier = getTier(d.margin_pct, !!d.leader);
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 right-3 sm:right-auto sm:min-w-[260px] rounded-xl bg-black/80 backdrop-blur border border-white/10 px-4 py-3 shadow-xl">
            <p className="text-sm font-semibold text-white mb-1">{d.region}</p>
            {d.leader ? (
              <>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.leader.color_hex || "#888" }} />
                  <span className="text-xs text-white/90">{d.leader.short_name || d.leader.name}</span>
                  <span className="text-xs font-semibold text-white ml-auto tabular-nums">{d.leader.pct.toFixed(1)}%</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border ml-1 ${
                      tier === "secure"
                        ? "bg-white/15 text-white border-white/20"
                        : tier === "lean"
                        ? "bg-white/10 text-white/80 border-white/15"
                        : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                    }`}
                  >
                    {tier === "secure" ? "SIGURNO" : tier === "lean" ? "UMERENO" : "NEIZVESNO"}
                  </span>
                </div>
                <div className="flex gap-3 text-[11px] text-white/50 tabular-nums">
                  <span>{d.processed_stations}/{d.total_stations} BM · {d.processed_pct.toFixed(0)}% obrađeno</span>
                  <span>· {d.turnout_pct.toFixed(1)}% izlaznost</span>
                  <span>· +{d.margin_pct.toFixed(1)}pp</span>
                </div>
              </>
            ) : (
              <p className="text-xs text-white/50">Nema još obrađenih rezultata</p>
            )}
          </div>
        );
      })()}
    </div>
  );
}
