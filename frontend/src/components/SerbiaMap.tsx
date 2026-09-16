"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import type { Feature, Geometry } from "geojson";
import {
  NO_DATA_COLOR,
  tieredLeaderFill,
  tossupFill,
  getTier,
  stripePatternId,
} from "@/lib/colorScale";
import type { MunicipalityRow, RegionResult, SwingInfo } from "@/lib/types";
import { formatCompact, formatPlaceName } from "@/lib/display";
import rikOpstine from "../../public/data/rik-opstine.json";

const GEO_REGIONI = "/data/serbia-regioni.geojson";

const DEFAULT_CENTER: [number, number] = [20.95, 44.05];
const DEFAULT_SCALE = 4200;

// Približni centroidi RIK regiona (lon/lat) za cifre populacije
const REGION_LABEL_POS: Record<string, [number, number]> = {
  "Београдски регион": [20.45, 44.82],
  "Регион Војводине": [19.9, 45.42],
  "Регион Шумадије и Западне Србије": [20.05, 43.85],
  "Регион Јужне и Источне Србије": [22.05, 43.3],
  "Регион Косово и Метохија": [20.9, 42.62],
};

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
  showRaceBadges = false,
  showTrend = false,
  onToggleTrend,
  swingMun,
  swingRegion,
  prevLabel = null,
  swingLoading = false,
}: {
  regions: RegionResult[];
  municipalities?: MunicipalityRow[];
  onSelectRegion: (regionName: string | null) => void;
  selectedRegion: string | null;
  selectedMunicipalityId?: number | null;
  onSelectMunicipality?: (id: number | null) => void;
  selectedRikOpstina?: RikOpstina | null;
  onSelectRikOpstina?: (op: RikOpstina | null) => void;
  // Bedževi trke (SIGURNO/UMERENO/NEIZVESNO) imaju smisla samo dok izbori traju
  showRaceBadges?: boolean;
  // Trend: strelice promene pobednika vs prethodni izbori
  showTrend?: boolean;
  onToggleTrend?: () => void;
  swingMun?: Map<number, SwingInfo>;
  swingRegion?: Map<string, SwingInfo>;
  prevLabel?: string | null;
  swingLoading?: boolean;
}) {
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null);
  const [hoveredOpstina, setHoveredOpstina] = useState<string | null>(null);
  const [selectedGeo, setSelectedGeo] = useState<RSMFeature | null>(null);
  const [regionGeos, setRegionGeos] = useState<RSMFeature[]>([]);
  // Toglovi (dole levo): cifre populacije + pogled svih opština
  const [showPopulation, setShowPopulation] = useState(false);
  const [showAllOpstine, setShowAllOpstine] = useState(false);

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
    // 1. direktno po data-id (rzs_code == RIK id) - globalno jedinstveno, npr. Palilula BG=70203 vs Nis=71323
    const byId = munByRikId.get(rikId);
    if (byId) return byId;
    // 2. po imenu SAMO unutar izabranog regiona - sprecava da se npr. niska Palilula
    //    zalepi za beogradsku kad kodovi nisu RIK (demo podaci)
    const norm = normalizeRik(rikName);
    const cand = munByNorm.get(norm);
    if (cand && selectedRegion && cand.region === selectedRegion) return cand;
    if (cand && !selectedRegion) return cand;
    return undefined;
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

  // Jedna opština kao SVG path (boja po lideru, klik kao na RIK mapi).
  // bleed=true: ivica u boji popune prekriva šavove između regiona.
  function renderOpstina(op: { id: string; name: string }, d: string, strokeScale = 1, bleed = false) {
    const mun = munForRik(op.id, op.name);
    const isSelMun = selectedMunicipalityId != null && mun?.id === selectedMunicipalityId;
    const isSelRik = selectedRikOpstina?.id === op.id;
    const isSel = isSelMun || isSelRik;
    const isHov = hoveredOpstina === op.id;
    const fill = (() => {
      if (!mun?.leader) return "#161a23";
      const t = getTier(mun.margin_pct, true);
      if (t === "tossup") return tossupFill(mun.leader.color_hex);
      return tieredLeaderFill(mun.leader.color_hex, mun.margin_pct);
    })();
    const edge = isSel || isHov ? "#ffffff" : bleed ? fill : "#dbe2ee";
    return (
      <path
        key={op.id}
        d={d}
        fill={fill}
        stroke={edge}
        strokeWidth={(isSel ? 2 : isHov ? 1.5 : bleed ? 1.6 : 1) * strokeScale}
        strokeLinejoin="round"
        strokeLinecap="round"
        shapeRendering="geometricPrecision"
        opacity={1}
        style={{ cursor: "pointer", outline: "none" }}
        onMouseEnter={() => setHoveredOpstina(op.id)}
        onMouseLeave={() => setHoveredOpstina(null)}
        onClick={() => {
          if (mun) {
            onSelectRikOpstina?.(null);
            onSelectMunicipality?.(mun.id === selectedMunicipalityId ? null : mun.id);
          } else {
            onSelectMunicipality?.(null);
            onSelectRikOpstina?.(isSelRik ? null : { id: op.id, name: op.name });
          }
        }}
      >
        <title>{formatPlaceName(op.name)}</title>
      </path>
    );
  }

  function tossupDefs() {
    return (
      <defs>
        {tossupColors.map((c) => (
          <pattern key={c} id={stripePatternId(c) ?? undefined} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width={8} height={8} fill="#161a23" />
            <rect width={4} height={8} fill={c} opacity={0.55} />
          </pattern>
        ))}
      </defs>
    );
  }

  // Strelice trenda (CNN stil): gore/dole/ravno, u boji lidera, sa vrednošću promene (pp)
  function trendArrow(
    change: number,
    color: string,
    s: number,
    title: string
  ) {
    const dir = change > 1 ? "up" : change < -1 ? "down" : "flat";
    const label = `${change > 0 ? "+" : ""}${change.toFixed(1)}`;
    const d =
      dir === "up"
        ? `M0 ${7 * s} L0 ${-4 * s} M${-4.5 * s} ${0.5 * s} L0 ${-7 * s} L${4.5 * s} ${0.5 * s}`
        : dir === "down"
        ? `M0 ${-7 * s} L0 ${4 * s} M${-4.5 * s} ${-0.5 * s} L0 ${7 * s} L${4.5 * s} ${-0.5 * s}`
        : `M${-6 * s} 0 L${6 * s} 0`;
    const w = (dir === "flat" ? 2.2 : 2.6) * s;
    const fg = dir === "flat" ? "#cbd5e1" : color;
    const textStyle: CSSProperties = { paintOrder: "stroke" };
    return (
      <g style={{ pointerEvents: "none" }}>
        <path d={d} stroke="#000" strokeWidth={w + 1.8 * s} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <path d={d} stroke={fg} strokeWidth={w} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <text
          textAnchor="middle"
          y={18 * s}
          fontSize={10 * s}
          fontWeight={800}
          fill="#fff"
          className="tabular-nums"
          stroke="#000"
          strokeWidth={2 * s}
          style={textStyle}
        >
          {label}
        </text>
        <title>{title}</title>
      </g>
    );
  }

  function swingTitle(info: SwingInfo): string {
    const base = prevLabel ? `Promena ${prevLabel}` : "Promena vs prethodni izbori";
    if (info.change_pp == null) return base;
    const sign = info.change_pp > 0 ? "+" : "";
    const prev = info.prev_party ? ` (tad: ${info.prev_party} ${info.prev_pct?.toFixed(1)}%)` : "";
    return `${base}: ${sign}${info.change_pp.toFixed(1)}pp${prev}`;
  }

  // SVG sloj opština jednog RIK regiona (zumirani pogled)
  function renderRikRegion(rikKey: string) {
    const rd = RIK.regions[rikKey];
    if (!rd) return null;
    return (
      <svg
        viewBox={`0 0 ${rd.width} ${rd.height}`}
        className="w-full h-full"
        style={{ background: "#0b0d12" }}
      >
        {tossupDefs()}
        {rd.municipalities.map((op) => renderOpstina(op, op.path))}
      </svg>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#0b0d12]">
      {/* Nije zumirano: 5 RIK regiona */}
      {!isLocked && !showAllOpstine && (
        <ComposableMap projection="geoMercator" projectionConfig={{ center: DEFAULT_CENTER, scale: DEFAULT_SCALE }} style={{ width: "100%", height: "100%" }}>
          <defs>
            {tossupColors.map((c) => (
              <pattern key={c} id={stripePatternId(c) ?? undefined} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
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
                  if (t === "tossup") return tossupFill(data.leader.color_hex);
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
          {/* Cifre populacije (upisani birači; bez spiska: zbir važećih glasova, isprekidano) po regionu */}
          {showPopulation &&
            regions.map((r) => {
              const pos = REGION_LABEL_POS[r.region];
              const reg = r.registered_voters || 0;
              const votesSum = (r.results ?? []).reduce((s, x) => s + (x.votes || 0), 0);
              const fallback = reg === 0 && votesSum > 0;
              const val = reg > 0 ? reg : votesSum;
              if (!pos || val <= 0) return null;
              const label = formatCompact(val);
              const w = label.length * 6 + 14;
              return (
                <Marker key={`pop-${r.region}`} coordinates={pos}>
                  <g style={{ pointerEvents: "none" }}>
                    <rect x={-w / 2} y={-11} width={w} height={20} rx={10} fill="rgba(0,0,0,0.72)" stroke="rgba(255,255,255,0.25)" strokeWidth={1} strokeDasharray={fallback ? "3 2" : undefined} />
                    <text textAnchor="middle" y={4} fontSize={11} fontWeight={700} fill="#fff" className="tabular-nums">
                      {label}
                    </text>
                    <title>{`${r.region}: ${val.toLocaleString("sr-RS")} ${reg > 0 ? "upisanih" : "važećih glasova (nema biračkog spiska)"}`}</title>
                  </g>
                </Marker>
              );
            })}
          {/* Strelice trenda po regionu */}
          {showTrend &&
            regions.map((r) => {
              const pos = REGION_LABEL_POS[r.region];
              const info = swingRegion?.get(r.region);
              if (!pos || !info || info.change_pp == null || !r.leader) return null;
              return (
                <Marker key={`tr-${r.region}`} coordinates={pos}>
                  <g transform={`translate(0, ${showPopulation ? 24 : 0})`}>
                    {trendArrow(info.change_pp, r.leader.color_hex || "#888", 1, swingTitle(info))}
                  </g>
                </Marker>
              );
            })}
        </ComposableMap>
      )}

      {/* Zumirano: RIK-ove prave opštine tog regiona (SVG paths, kao RIK) */}
      {isLocked && selectedRegion && rikRegion && renderRikRegion(REGION_TO_RS[selectedRegion] ?? "")}

      {/* Sve opštine: svih 5 regiona kao prozori, bez ulaska klikom */}
      {!isLocked && showAllOpstine && (
        <div className="absolute inset-0 overflow-y-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-2">
            {Object.entries(REGION_TO_RS).map(([regionName, rikKey]) => {
              const rd = RIK.regions[rikKey];
              if (!rd) return null;
              const data = regionByName.get(regionName);
              return (
                <div key={rikKey} className="rounded-xl overflow-hidden border border-white/10 bg-[#0b0d12]">
                  <button
                    onClick={() => onSelectRegion(regionName)}
                    className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-white/5 transition-colors"
                  >
                    {data?.leader && (
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ background: data.leader.color_hex || "#888" }}
                      />
                    )}
                    <span className="text-[11px] font-medium text-white/80 truncate">
                      {regionName}
                    </span>
                    <span className="text-[10px] text-white/35 ml-auto shrink-0 tabular-nums">
                      {rd.municipalities.length} opština
                    </span>
                  </button>
                  <div className="h-44 sm:h-52">{renderRikRegion(rikKey)}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {isLocked && (
        <button onClick={() => { setSelectedGeo(null); onSelectRegion(null); }} className="absolute top-3 left-3 rounded-full bg-black/70 backdrop-blur px-3.5 py-1.5 text-xs font-medium text-white border border-white/15 hover:bg-black/85 shadow-lg">
          ← Svi regioni
        </button>
      )}

      {/* Toglovi dole levo: populacija + sve opštine */}
      {!isLocked && (
        <div className="absolute bottom-3 left-3 flex flex-wrap items-center gap-1.5 sm:gap-2 max-w-[70vw]">
          <button
            onClick={() => setShowPopulation((v) => !v)}
            title="Prikaži broj upisanih birača po regionu"
            className={`rounded-full backdrop-blur px-3 sm:px-3.5 py-1.5 text-[11px] sm:text-xs font-medium border shadow-lg transition-colors ${
              showPopulation
                ? "bg-white text-black border-white"
                : "bg-black/70 text-white border-white/15 hover:bg-black/85"
            }`}
          >
            Populacija
          </button>
          <button
            onClick={() => setShowAllOpstine((v) => !v)}
            title="Prikaži sve opštine svih regiona odjednom"
            className={`rounded-full backdrop-blur px-3 sm:px-3.5 py-1.5 text-[11px] sm:text-xs font-medium border shadow-lg transition-colors ${
              showAllOpstine
                ? "bg-white text-black border-white"
                : "bg-black/70 text-white border-white/15 hover:bg-black/85"
            }`}
          >
            Opštine
          </button>
          <button
            onClick={() => onToggleTrend?.()}
            title="Strelice promene pobednika u odnosu na prethodne izbore"
            className={`rounded-full backdrop-blur px-3 sm:px-3.5 py-1.5 text-[11px] sm:text-xs font-medium border shadow-lg transition-colors ${
              showTrend
                ? "bg-white text-black border-white"
                : "bg-black/70 text-white border-white/15 hover:bg-black/85"
            }`}
          >
            Trend
          </button>
          {showTrend && swingLoading && (
            <span className="rounded-full bg-black/70 backdrop-blur border border-white/15 px-3 py-1.5 text-xs text-white/70 flex items-center gap-2 shadow-lg">
              <span className="w-3 h-3 rounded-full border-2 border-white/20 border-t-white/80 animate-spin" />
              Trend…
            </span>
          )}
        </div>
      )}

      <div className="absolute bottom-3 right-3 rounded-xl bg-black/70 backdrop-blur border border-white/10 px-3 py-2 hidden sm:flex items-center gap-3">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30] border border-white/20" /><span className="text-[10px] text-white/70">Sigurno ≥10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-[#D85A30]/60 border border-white/20" /><span className="text-[10px] text-white/70">Umereno 5–10%</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-white/20" style={{ background: `repeating-linear-gradient(45deg, #161a23 0 3px, #D85A30 3px 6px)` }} /><span className="text-[10px] text-white/70">Neizvesno &lt;5%</span></span>
      </div>

      {!isLocked && !showAllOpstine && hoveredRegion && (() => {
        const d = regionByName.get(hoveredRegion);
        if (!d) return null;
        const tier = getTier(d.margin_pct, !!d.leader);
        return (
          <div className="pointer-events-none absolute bottom-16 left-3 right-3 sm:right-auto sm:min-w-[260px] rounded-xl bg-black/80 backdrop-blur border border-white/10 px-4 py-3 shadow-xl">
            <p className="text-sm font-semibold text-white mb-1">{d.region}</p>
            {d.leader ? (
              <>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: d.leader.color_hex || "#888" }} />
                  <span className="text-xs text-white/90">{d.leader.short_name || d.leader.name}</span>
                  <span className="text-xs font-semibold text-white ml-auto tabular-nums">{d.leader.pct.toFixed(1)}%</span>
                  {showRaceBadges && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border ml-1 ${tier === "secure" ? "bg-white/15 text-white border-white/20" : tier === "lean" ? "bg-white/10 text-white/80 border-white/15" : "bg-amber-500/20 text-amber-300 border-amber-500/30"}`}>
                      {tier === "secure" ? "SIGURNO" : tier === "lean" ? "UMERENO" : "NEIZVESNO"}
                    </span>
                  )}
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
            {selectedRegion} · {rikRegion?.municipalities.length ?? 0} opština · klik na opštinu za detalje
          </p>
        </div>
      )}

      {hoveredOpstina && (() => {
        // Nadji opštinu u zaključanom regionu ili u prozorima svih opština
        const pools = isLocked && rikRegion
          ? [rikRegion.municipalities]
          : showAllOpstine
          ? Object.values(RIK.regions).map((r) => r.municipalities)
          : [];
        let op: { id: string; name: string } | undefined;
        for (const pool of pools) {
          op = pool.find((x) => x.id === hoveredOpstina);
          if (op) break;
        }
        if (!op) return null;
        const mun = munForRik(op.id, op.name);
        const sw = mun ? swingMun?.get(mun.id) : undefined;
        const trendLine =
          showTrend && sw && sw.change_pp != null
            ? ` · trend ${sw.change_pp > 0 ? "+" : ""}${sw.change_pp.toFixed(1)}pp${prevLabel ? ` ${prevLabel}` : ""}`
            : "";
        return (
          <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-black/80 backdrop-blur border border-white/10 px-3 py-2 shadow-xl max-w-[280px]">
            <p className="text-xs font-semibold text-white">{formatPlaceName(op.name)}</p>
            {mun?.leader ? (
              <p className="text-[11px] text-white/60 tabular-nums mt-0.5">
                {mun.leader.short_name} {mun.leader.pct.toFixed(1)}% · +{mun.margin_pct.toFixed(1)}pp · {mun.processed_pct.toFixed(0)}% obrađeno{trendLine}
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
