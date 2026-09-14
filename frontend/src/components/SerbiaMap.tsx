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
import rikOpstine from "../../public/data/rik-opstine.json";

const GEO_REGIONI = "/data/serbia-regioni.geojson";

const DEFAULT_CENTER: [number, number] = [20.95, 44.05];
const DEFAULT_SCALE = 4200;

// RIK region -> rs kod (za rik-opstine.json)
const REGION_TO_RS: Record<string, string> = {
  "Београдски регион": "rs11",
  "Регион Војводине": "rs12",
  "Регион Шумадије и Западне Србије": "rs21",
  "Регион Јужне и Источне Србије": "rs22",
  "Регион Косово и Метохија": "rs23",
};

type RikRegionData = {
  rik_region: string;
  width: number;
  height: number;
  municipalities: { id: string; name: string; path: string }[];
};
const RIK = rikOpstine as { regions: Record<string, RikRegionData> };

type RSMFeature = Feature<Geometry> & { rsmKey: string; svgPath: string };
function nameOf(f: RSMFeature): string {
  return (f.properties as { name?: string } | null)?.name ?? "";
}
function normalize(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/city|municipality|opstina|gradska opstina/g, "")
    .replace(/[^a-zа-яё]/g, "")
    .trim();
}
// RIK imena su ćirilica caps (ПАЛИЛУЛА) -> normalizuj i transliteruj za match sa DB (Palilula)
function normalizeRik(name: string): string {
  const cyr: Record<string, string> = {
    а: "a", б: "b", в: "v", г: "g", д: "d", ђ: "dj", е: "e", ж: "z", з: "z",
    и: "i", ј: "j", к: "k", л: "l", љ: "lj", м: "m", н: "n", њ: "nj",
    о: "o", п: "p", р: "r", с: "s", т: "t", ћ: "c", у: "u", ф: "f",
    х: "h", ц: "c", ч: "c", џ: "dz", ш: "s",
  };
  return name
    .toLowerCase()
    .split("")
    .map((ch) => cyr[ch] ?? ch)
    .join("")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z]/g, "")
    .trim();
}

export type RikOpstina = { id: string; name: string };

export default function SerbiaMap({
  regions,
  municipalities,
  onSelectRegion,
  selectedRegion,
  selectedMunicipalityId,
  onSelectMunicipality,
  selectedRikOpstina,
  onSelectRikOpstina,
}: {
  regions: RegionResult[];
  municipalities?: MunicipalityRow[];
  onSelectRegion: (regionName: string | null) => void;
  selectedRegion: string | null;
  selectedMunicipalityId?: number | null;
  onSelectMunicipality?: (id: number | null) => void;
  selectedRikOpstina?: RikOpstina | null;
  onSelectRikOpstina?: (op: RikOpstina | null) => void;
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

  // DB match: prvo po rzs_code == RIK id, pa po imenu
  const munByRikId = useMemo(() => {
    const m = new Map<string, MunicipalityRow>();
    if (!municipalities) return m;
    for (const mun of municipalities) {
      if (mun.rzs_code) m.set(String(mun.rzs_code), mun);
    }
    return m;
  }, [municipalities]);

  const munByNorm = useMemo(() => {
    const m = new Map<string, MunicipalityRow>();
    if (!municipalities) return m;
    for (const mun of municipalities) {
      const k = normalize(mun.name);
      if (!m.has(k)) m.set(k, mun);
    }
    return m;
  }, [municipalities]);

  function munForRik(rikId: string, rikName: string): MunicipalityRow | undefined {
    // 1. direktno po data-id (nakon bootstrap-a rzs_code == RIK id)
    const byId = munByRikId.get(rikId);
    if (byId) return byId;
    // 2. po imenu (transliteracija)
    const norm = normalizeRik(rikName);
    return munByNorm.get(norm);
  }

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

  // RIK opštine za izabrani region
  const rikRegion = selectedRegion ? RIK.regions[REGION_TO_RS[selectedRegion] ?? ""] : undefined;

  function handleRegionClick(g: RSMFeature) {
    const n = nameOf(g);
    if (selectedRegion === n) { setSelectedGeo(null); onSelectRegion(null); return; }
    setSelectedGeo(g);
    onSelectRegion(n);
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#0b0d12]">
      {/* Nije zumirano: 5 RIK regiona */}
      {!isLocked && (
        <ComposableMap projection="geoMercator" projectionConfig={{ center: DEFAULT_CENTER, scale: DEFAULT_SCALE }} style={{ width: "100%", height: "100%" }}>
          <defs>
            {tossupColors.map((c) => (
              <pattern key={c} id={stripePatternId(c)} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width={8} height={8} fill="#161a23" />
                <rect width={4} height={8} fill={c} opacity={0.55} />
              </pattern>
            ))}
          </defs>
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
        </ComposableMap>
      )}

      {/* Zumirano: RIK-ove prave opštine tog regiona (SVG paths, kao RIK) */}
      {isLocked && selectedRegion && rikRegion && (
        <svg
          viewBox={`0 0 ${rikRegion.width} ${rikRegion.height}`}
          className="w-full h-full"
          style={{ background: "#0b0d12" }}
        >
          <defs>
            {tossupColors.map((c) => (
              <pattern key={c} id={stripePatternId(c)} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width={8} height={8} fill="#161a23" />
                <rect width={4} height={8} fill={c} opacity={0.55} />
              </pattern>
            ))}
          </defs>
          {rikRegion.municipalities.map((op) => {
            const mun = munForRik(op.id, op.name);
            const isSelMun = selectedMunicipalityId != null && mun?.id === selectedMunicipalityId;
            const isSelRik = selectedRikOpstina?.id === op.id;
            const isSel = isSelMun || isSelRik;
            const isHov = hoveredOpstina === op.id;
            const fill = (() => {
              if (!mun?.leader) return "#161a23";
              const t = getTier(mun.margin_pct, true);
              if (t === "tossup") return `url(#${stripePatternId(mun.leader.color_hex)})`;
              return tieredLeaderFill(mun.leader.color_hex, mun.margin_pct);
            })();
            const hasData = !!mun?.leader;
            return (
              <path
                key={op.id}
                d={op.path}
                fill={fill}
                stroke={isSel ? "#ffffff" : isHov ? "#ffffff" : "#e8edf5"}
                strokeWidth={isSel ? 2.2 : isHov ? 1.6 : 0.9}
                opacity={1}
                style={{ cursor: "pointer", outline: "none" }}
                onMouseEnter={() => setHoveredOpstina(op.id)}
                onMouseLeave={() => setHoveredOpstina(null)}
                onClick={() => {
                  if (mun) {
                    // ima DB zapis -> prikazi rezultate, ocisti RIK-only selekciju
                    onSelectRikOpstina?.(null);
                    onSelectMunicipality?.(mun.id === selectedMunicipalityId ? null : mun.id);
                  } else {
                    // nema rezultata -> svejedno selektuj, prikazi ime + poruku
                    onSelectMunicipality?.(null);
                    onSelectRikOpstina?.(isSelRik ? null : { id: op.id, name: op.name });
                  }
                }}
              >
                <title>{op.name}</title>
              </path>
            );
          })}
        </svg>
      )}

      {isLocked && (
        <button onClick={() => { setSelectedGeo(null); onSelectRegion(null); }} className="absolute top-3 left-3 rounded-full bg-black/70 backdrop-blur px-3.5 py-1.5 text-xs font-medium text-white border border-white/15 hover:bg-black/85 shadow-lg">
          ← Svi regioni
        </button>
      )}

      <div className="absolute bottom-3 right-3 rounded-xl bg-black/70 backdrop-blur border border-white/10 px-3 py-2 hidden sm:flex items-center gap-3">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30] border border-white/20" /><span className="text-[10px] text-white/70">Sigurno ≥10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30]/60 border border-white/20" /><span className="text-[10px] text-white/70">Umereno 5–10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-white/20" style={{ background: `repeating-linear-gradient(45deg, #161a23 0 3px, #D85A30 3px 6px)` }} /><span className="text-[10px] text-white/70">Neizvesno &lt;5%</span></span>
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

      {isLocked && selectedRegion && !hoveredOpstina && (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/60 backdrop-blur border border-white/10 px-3 py-2">
          <p className="text-[11px] text-white/70">
            {selectedRegion} — {rikRegion?.municipalities.length ?? 0} opština (RIK oblici) · klik na opštinu za detalje
          </p>
        </div>
      )}

      {isLocked && hoveredOpstina && rikRegion && (() => {
        const op = rikRegion.municipalities.find((x) => x.id === hoveredOpstina);
        if (!op) return null;
        const mun = munForRik(op.id, op.name);
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/80 backdrop-blur border border-white/10 px-3 py-2 shadow-xl max-w-[280px]">
            <p className="text-xs font-semibold text-white">{op.name}</p>
            {mun?.leader ? (
              <p className="text-[11px] text-white/60 tabular-nums mt-0.5">
                {mun.leader.short_name} {mun.leader.pct.toFixed(1)}% · +{mun.margin_pct.toFixed(1)}pp · {mun.processed_pct.toFixed(0)}% obrađeno
              </p>
            ) : (
              <p className="text-[11px] text-white/40 mt-0.5">Nema rezultata u bazi — klik za detalje</p>
            )}
          </div>
        );
      })()}
    </div>
  );
}
