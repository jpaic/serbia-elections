// Tamna pozadina i neutralne boje
const NO_DATA_FILL = "#20242c";
export const NO_DATA_COLOR = NO_DATA_FILL;

// Helperi
function hexToRgb(hex: string) {
  const clean = hex.replace("#", "");
  const n = parseInt(clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255] as const;
}

function rgbToHex(r: number, g: number, b: number) {
  return (
    "#" +
    [r, g, b]
      .map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0"))
      .join("")
  );
}

// Sekvencijalna skala za fallback (processed_pct)
const STOPS: [number, string][] = [
  [0, "#1c2128"],
  [25, "#25344d"],
  [50, "#2c4870"],
  [75, "#356ba8"],
  [100, "#3b82d6"],
];

export function processedColor(pct: number): string {
  const clamped = Math.max(0, Math.min(100, pct));
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [p0, c0] = STOPS[i];
    const [p1, c1] = STOPS[i + 1];
    if (clamped >= p0 && clamped <= p1) {
      const t = (clamped - p0) / (p1 - p0);
      const [r0, g0, b0] = hexToRgb(c0);
      const [r1, g1, b1] = hexToRgb(c1);
      return rgbToHex(r0 + (r1 - r0) * t, g0 + (g1 - g0) * t, b0 + (b1 - b0) * t);
    }
  }
  return STOPS[STOPS.length - 1][1];
}

// Tiered leader bojenje: sigurno / lean / tossup
export type Tier = "secure" | "lean" | "tossup" | "no-data";

export function getTier(marginPct: number | null | undefined, hasLeader: boolean): Tier {
  if (!hasLeader) return "no-data";
  const m = marginPct ?? 0;
  if (m >= 10) return "secure";
  if (m >= 5) return "lean";
  return "tossup";
}

export function leaderColor(
  partyColorHex: string | null | undefined,
  marginPct: number | null | undefined
): string {
  // zadrzano za backward compat - mapira na tiered
  return tieredLeaderFill(partyColorHex, marginPct);
}

export function tieredLeaderFill(
  partyColorHex: string | null | undefined,
  marginPct: number | null | undefined
): string {
  if (!partyColorHex) return NO_DATA_FILL;
  const tier = getTier(marginPct, true);
  const [r, g, b] = hexToRgb(partyColorHex);
  const bg = hexToRgb("#12151b");
  if (tier === "secure") {
    // puna boja, blago potamnjena da ne bode oči na tamnoj mapi
    const blend = 0.92;
    return rgbToHex(bg[0] + (r - bg[0]) * blend, bg[1] + (g - bg[1]) * blend, bg[2] + (b - bg[2]) * blend);
  }
  if (tier === "lean") {
    // svetlija, isprana nijansa
    const blend = 0.58;
    return rgbToHex(bg[0] + (r - bg[0]) * blend, bg[1] + (g - bg[1]) * blend, bg[2] + (b - bg[2]) * blend);
  }
  // tossup - ne vraćamo solid, koristi se pattern; fallback neutralna
  return "#2a2f3a";
}

// Za dijagonalne linije - id patterna po boji (null-safe: bez boje nema pruga)
export function stripePatternId(partyColorHex: string | null | undefined): string | null {
  if (!partyColorHex) return null;
  return `stripe-${partyColorHex.replace("#", "").toLowerCase()}`;
}

// Tossup fill: pruge ako ima boje, inace neutralna (nikad ne puca na null)
export function tossupFill(partyColorHex: string | null | undefined): string {
  const id = stripePatternId(partyColorHex);
  return id ? `url(#${id})` : "#2a2f3a";
}

// Helper za legendu
export function tierLabel(tier: Tier): string {
  if (tier === "secure") return "Sigurno (≥10%)";
  if (tier === "lean") return "Umereno (5–10%)";
  if (tier === "tossup") return "Neizvesno (<5%)";
  return "Nema podataka";
}
