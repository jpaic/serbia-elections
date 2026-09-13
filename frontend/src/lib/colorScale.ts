// Sekvencijalna skala plave boje za % obrađenih biračkih mesta po regionu.
// 0% = svetlo siva (nema podataka), 100% = tamno plava.
const STOPS: [number, string][] = [
  [0, "#E6E5DD"],
  [25, "#B5D4F4"],
  [50, "#85B7EB"],
  [75, "#378ADD"],
  [100, "#0C447C"],
];

function hexToRgb(hex: string) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(r: number, g: number, b: number) {
  return (
    "#" +
    [r, g, b]
      .map((v) => Math.round(v).toString(16).padStart(2, "0"))
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
