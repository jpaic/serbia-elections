// Sekvencijalna skala (sivo -> plavo) za % obrađenih biračkih mesta.
// Koristi se kao fallback kad za region/opštinu još nema rezultata.
const STOPS: [number, string][] = [
  [0, "#1c2128"],
  [25, "#25344d"],
  [50, "#2c4870"],
  [75, "#356ba8"],
  [100, "#3b82d6"],
];

function hexToRgb(hex: string) {
  const clean = hex.replace("#", "");
  const n = parseInt(clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(r: number, g: number, b: number) {
  return (
    "#" +
    [r, g, b]
      .map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0"))
      .join("")
  );
}

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

// "CNN stil": boja pobedničke partije u regionu, zatamnjena/posvetljena u zavisnosti
// od margine nad drugoplasiranim — tesna trka je bleđa nijansa, ubedljiva pobeda je
// puna, zasićena boja. Kad okrug nema obrađenih rezultata, vraća neutralnu sivu.
const NO_DATA_FILL = "#20242c";

export function leaderColor(
  partyColorHex: string | null | undefined,
  marginPct: number | null | undefined
): string {
  if (!partyColorHex) return NO_DATA_FILL;
  const [r, g, b] = hexToRgb(partyColorHex);
  // margina 0 -> mešano sa pozadinom (bleđe), margina 40+ -> puna boja partije
  const m = Math.max(0, Math.min(40, marginPct ?? 0));
  const strength = 0.35 + (m / 40) * 0.65; // 0.35 - 1.0
  const bg = hexToRgb("#12151b");
  return rgbToHex(
    bg[0] + (r - bg[0]) * strength,
    bg[1] + (g - bg[1]) * strength,
    bg[2] + (b - bg[2]) * strength
  );
}

export const NO_DATA_COLOR = NO_DATA_FILL;
