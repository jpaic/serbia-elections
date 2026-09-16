// RIK nazivi regiona su ćirilica, stari demo podaci latinica — prihvati oba
export function isDiasporaRegion(name: string | null | undefined): boolean {
  return name === "Inostranstvo" || name === "Иностранство";
}
export function isZavodiRegion(name: string | null | undefined): boolean {
  return (
    name === "Zavodi za izvršenje krivičnih sankcija" ||
    name === "Заводи за извршење кривичних санкција"
  );
}

// Kompaktan broj za cifre na mapi: 1600000 -> "1,6M", 45000 -> "45 hilj."
export function formatCompact(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString("sr-RS", { maximumFractionDigits: 1 })}M`;
  }
  if (n >= 1_000) {
    return `${Math.round(n / 1_000).toLocaleString("sr-RS")} hilj.`;
  }
  return n.toLocaleString("sr-RS");
}

// Glagol pobednika: sadašnje vreme dok traju, prošlo za završene izbore
export function leaderVerb(status?: string, capitalized = false): string {
  const past = status === "closed";
  if (capitalized) return past ? "Pobedio" : "Vodi";
  return past ? "pobedio" : "vodi";
}

// "ПАЛИЛУЛА" -> "Палилула", "ПЕТРОВАЦ НА МЛАВИ" -> "Петровац на Млави"
const SMALL_WORDS = new Set(["на", "у", "и", "са", "с", "из", "од", "до", "за", "по", "о", "а"]);
export function formatPlaceName(name: string): string {
  const words = name.toLowerCase().split(/\s+/);
  return words
    .map((w, i) =>
      i > 0 && SMALL_WORDS.has(w)
        ? w
        : w
            .split("-")
            .map((p) => (p.length > 0 ? p.charAt(0).toUpperCase() + p.slice(1) : p))
            .join("-")
    )
    .join(" ");
}
